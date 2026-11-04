#!/usr/bin/env bash
# One-command environment setup for eval-hawthorne-effect.
# Usage (from the repo root):  bash scripts/setup_env.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# If the repo sits in an iCloud-synced folder, iCloud marks files inside dot-folders
# (like .venv) with the macOS "hidden" flag some time after creation, and Python
# skips hidden .pth files, which breaks the editable installs. So the real venv
# lives outside the repo and .venv is a symlink to it.
VENV_TARGET="${HAWTHORNE_VENV:-$HOME/.venvs/eval-hawthorne-effect}"

# 1. Make sure the pinned ImpossibleBench submodule is present.
git submodule update --init --recursive

# 2. Create the out-of-repo venv and link it (uv refuses a dangling link).
if [[ -e .venv && ! -L .venv ]]; then
  echo "Removing in-repo .venv (replacing with link to $VENV_TARGET)"
  rm -rf .venv
fi
if [[ ! -x "$VENV_TARGET/bin/python" ]]; then
  uv venv "$VENV_TARGET" --python 3.12
fi
ln -sfn "$VENV_TARGET" .venv

# 3. Install / refresh from uv.lock.
uv sync --reinstall-package hawthorne

# 4. Belt and braces: clear any hidden flags on the real venv (no-op off macOS).
if [[ "$(uname)" == "Darwin" ]]; then
  chflags -R nohidden "$VENV_TARGET"
fi

# 5. Check.
uv run --no-sync python -c "import impossiblebench, hawthorne; print('OK: impossiblebench + hawthorne import')"
