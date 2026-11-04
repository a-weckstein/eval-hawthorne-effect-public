"""Inspect model connector "glmraw": GLM-5.3 via OpenRouter's raw /completions endpoint, with reasoning continuation.

Why: OpenRouter's chat endpoint cannot continue a partial
reasoning trace for GLM-5.3-flash. The raw endpoint can, if we write GLM's chat template ourselves and stop inside an
open <think> block. This connector renders every call that way, so all arms of the reasoning-edit experiment share
one endpoint.

Usage:  model="glmraw/z-ai/glm-5.3-flash", model_args={"provider": "InferenceNet"}
Partial reasoning: if the LAST input message is a ChatMessageAssistant with metadata {"partial": True}, its reasoning
is rendered as an OPEN <think> block and the model continues it. The returned message holds the full reasoning
(prefix + continuation) so later attempts and analysis see the edited trace. A partial message that is not last
(i.e. already followed by the completed reply) is dropped when rendering.

Rendering follows HF zai-org/GLM-5.3-Flash chat_template.jinja @ 46a050be for system / user / assistant messages
without tools.
"""

from __future__ import annotations

import os
import ssl
from typing import Any

import httpx
from inspect_ai.model import (ChatCompletionChoice, ChatMessage, ChatMessageAssistant, ContentReasoning, ContentText,
                              GenerateConfig, ModelAPI, ModelOutput, ModelUsage, modelapi)
from inspect_ai.model._model_call import ModelCall
from inspect_ai.tool import ToolChoice, ToolInfo

OPENROUTER_COMPLETIONS = "https://openrouter.ai/api/v1/completions"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


class GLMRawBudgetExceeded(RuntimeError):
    """Raised before a call once the run's OpenRouter-reported spend reaches budget_usd. Never retried."""


class GLMRawHTTPError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"OpenRouter {status}: {detail[:300]}")
        self.status = status


def _text(m: ChatMessage) -> str:
    if isinstance(m.content, str):
        return m.content
    return "".join(c.text for c in m.content if isinstance(c, ContentText))


def _reasoning(m: ChatMessage) -> str | None:
    if isinstance(m.content, str):
        return None
    parts = [c.reasoning for c in m.content if isinstance(c, ContentReasoning)]
    return "".join(parts) if parts else None


def is_partial(m: ChatMessage) -> bool:
    return m.role == "assistant" and bool((m.metadata or {}).get("partial"))


def effort_label(reasoning_effort: str | None) -> str:
    # Template: effective effort = reasoning_effort if in ['low', 'high'] else 'max'; rendered capitalised.
    return reasoning_effort.capitalize() if reasoning_effort in ("low", "high") else "Max"


def render_glm(messages: list[ChatMessage], reasoning_effort: str | None) -> tuple[str, str | None]:
    """Return (prompt, open_prefix). open_prefix is the partial reasoning being continued, or None."""
    msgs = [m for i, m in enumerate(messages) if not (is_partial(m) and i < len(messages) - 1)]
    out = ["[gMASK]<sop>", f"<|system|>Reasoning Effort: {effort_label(reasoning_effort)}"]
    open_prefix = None
    for i, m in enumerate(msgs):
        if m.role == "system":
            out.append(f"<|system|>{_text(m)}")
        elif m.role == "user":
            out.append(f"<|user|>{_text(m)}")
        elif m.role == "assistant":
            r = _reasoning(m)
            if i == len(msgs) - 1 and is_partial(m):
                open_prefix = r or ""
                out.append(f"<|assistant|><think>{open_prefix}")
                return "".join(out), open_prefix
            content = _text(m)
            if r is None and "</think>" in content:  # template fallback: reasoning inline in content
                r = content.split("</think>")[0].split("<think>")[-1]
                content = content.split("</think>")[-1]
            out.append("<|assistant|>" + (f"<think>{r}</think>" if r is not None else "<think></think>") + content.strip())
        else:
            raise ValueError(f"glmraw renders system/user/assistant only; got role {m.role!r}")
    out.append("<|assistant|><think>")
    return "".join(out), None


@modelapi(name="glmraw")
class GLMRawAPI(ModelAPI):
    def __init__(self, model_name: str, base_url: str | None = None, api_key: str | None = None,
                 config: GenerateConfig = GenerateConfig(), provider: str | None = None,
                 transport: Any = None, budget_usd: float | None = None, **model_args: Any) -> None:
        super().__init__(model_name, base_url, api_key, ["OPENROUTER_API_KEY"], config)
        self.provider = provider
        # Hard run-level spending cap: cumulative OpenRouter-reported cost of every call made by this model
        # instance. Checked before each call, so a run overshoots by at most one call's cost.
        self.budget_usd = budget_usd
        self.spent_usd = 0.0
        self.transport = transport  # tests inject httpx.MockTransport; None = real network
        if self.api_key is None and transport is None:
            self.api_key = os.environ.get("OPENROUTER_API_KEY")
            if not self.api_key:
                raise RuntimeError("OPENROUTER_API_KEY not set (load .env first)")

    def max_tokens(self) -> int | None:
        return 64000

    def should_retry(self, ex: BaseException) -> bool:
        """Retry rate limits, server errors, timeouts and dropped connections; not bad requests."""
        if isinstance(ex, GLMRawBudgetExceeded):
            return False
        if isinstance(ex, GLMRawHTTPError):
            return ex.status in RETRY_STATUS
        # ssl.SSLError / ConnectionError: raw TLS or socket failures that httpx does not always wrap (2 lost episodes
        # on 2026-10-21).
        return isinstance(ex, (httpx.TimeoutException, httpx.TransportError, ValueError, ssl.SSLError, ConnectionError)) and not isinstance(ex, TypeError)

    async def generate(self, input: list[ChatMessage], tools: list[ToolInfo], tool_choice: ToolChoice,
                       config: GenerateConfig) -> tuple[ModelOutput | Exception, ModelCall]:
        if tools:
            raise ValueError("glmraw does not support tools")
        if self.budget_usd is not None and self.spent_usd >= self.budget_usd:
            raise GLMRawBudgetExceeded(f"run budget ${self.budget_usd:.2f} reached (spent ${self.spent_usd:.4f}); no further calls")
        prompt, open_prefix = render_glm(input, config.reasoning_effort)
        body: dict[str, Any] = {"model": self.model_name, "prompt": prompt, "max_tokens": config.max_tokens or 64000}
        if config.temperature is not None:
            body["temperature"] = config.temperature
        if self.provider:
            body["provider"] = {"order": [self.provider], "allow_fallbacks": False}
        async with httpx.AsyncClient(transport=self.transport, timeout=httpx.Timeout(1800.0)) as client:
            resp = await client.post(OPENROUTER_COMPLETIONS, json=body,
                                     headers={"Authorization": f"Bearer {self.api_key or 'test'}"})
        call = ModelCall.create(request={**body, "prompt": f"<{len(prompt)} chars; open_prefix={open_prefix is not None}>"},
                                response=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"status": resp.status_code, "text": resp.text[:500]})
        if resp.status_code != 200:
            raise GLMRawHTTPError(resp.status_code, resp.text)
        data = resp.json()  # a malformed body raises ValueError (retried)
        if "error" in data:  # OpenRouter can return 200 with an error object
            err = data["error"]
            raise GLMRawHTTPError(int(err.get("code", 500)) if isinstance(err, dict) and str(err.get("code", "")).isdigit() else 500, str(err))
        ch = data["choices"][0]
        cont_reasoning = ch.get("reasoning") or ""
        text = ch.get("text") or ""
        full_reasoning = (open_prefix or "") + cont_reasoning
        content: list[Any] = []
        if full_reasoning:
            content.append(ContentReasoning(reasoning=full_reasoning))
        content.append(ContentText(text=text))
        u = data.get("usage") or {}
        self.spent_usd += float(u.get("cost") or 0.0)
        details = u.get("prompt_tokens_details") or {}
        usage = ModelUsage(input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0),
                           total_tokens=u.get("total_tokens", 0), input_tokens_cache_read=details.get("cached_tokens"),
                           reasoning_tokens=(u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                           total_cost=u.get("cost"))
        stop = "max_tokens" if ch.get("finish_reason") == "length" else "stop"
        msg = ChatMessageAssistant(content=content, model=self.model_name, source="generate",
                                   metadata={"continued_from_prefix": open_prefix is not None,
                                             "prefix_chars": len(open_prefix or ""), "provider": data.get("provider")})
        return ModelOutput(model=self.model_name, choices=[ChatCompletionChoice(message=msg, stop_reason=stop)],
                           usage=usage), call
