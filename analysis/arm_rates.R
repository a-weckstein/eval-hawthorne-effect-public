#!/usr/bin/env Rscript
# Per-arm cheating rates and paired contrasts from one run's samples.csv (written by scripts/summarize_logs.py).
#
# Usage:  Rscript analysis/arm_rates.R results/<date>_<run>/samples.csv [--control neutral] [--keep-dead] [--endpoint cheat_in_loop]
#
# Dead-task rule: lcbhard_35 and lcbhard_87 have no check() wrapper and a single
# non-contradictory assertion, so they can never be passed in-loop and do not present the impossible-test dilemma.
# They are EXCLUDED from every cheating-rate denominator, confidence interval and paired test, and KEPT in the
# cost / health tallies. --keep-dead keeps them in (n = 103 / 60).
#
# Statistics: rate CIs are Wilson score and Clopper-Pearson (exact); differences vs the control arm are paired on
# task, with Newcombe's (1998) method 10 interval (Wilson-based, with the phi correction) and an exact McNemar test
# on the discordant tasks. With --keep-dead, numbers were checked against hand-computed tables (2026-10-18).

suppressPackageStartupMessages(library(DescTools))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("usage: Rscript analysis/arm_rates.R results/<run>/samples.csv [--control neutral] [--keep-dead] [--endpoint cheat_in_loop]")
csv <- args[1]
getopt <- function(flag, default) { i <- match(flag, args); if (is.na(i)) default else args[i + 1] }
control  <- getopt("--control", "neutral")
endpoint <- getopt("--endpoint", "cheat_in_loop")
keep_dead <- "--keep-dead" %in% args
DEAD <- c("lcbhard_35", "lcbhard_87")

d <- read.csv(csv, stringsAsFactors = FALSE)
stopifnot(all(c("arm", "sample", endpoint, "n_cut_off", "cost_usd") %in% names(d)))
d$cheat <- d[[endpoint]] %in% c("True", "TRUE", TRUE)
all_rows <- d
if (!keep_dead) d <- d[!d$sample %in% DEAD, ]
dead_present <- intersect(DEAD, unique(all_rows$sample))

cat(sprintf("run: %s | endpoint: %s | control: %s | dead tasks present: %s | %s\n\n", csv, endpoint, control,
            if (length(dead_present)) paste(dead_present, collapse = ", ") else "none",
            if (keep_dead) "dead tasks KEPT (pre-D21 accounting)" else "dead tasks EXCLUDED from rates (D21)"))

# Newcombe (1998) method 10: CI for a paired difference p1 - p2 from the 2x2 table (e = both, f = 1 only, g = 2 only, h = neither).
newcombe_paired <- function(e, f, g, h, conf = 0.95) {
  n <- e + f + g + h; p1 <- (e + f) / n; p2 <- (e + g) / n
  w1 <- BinomCI(e + f, n, conf.level = conf, method = "wilson"); w2 <- BinomCI(e + g, n, conf.level = conf, method = "wilson")
  l1 <- w1[, "lwr.ci"]; u1 <- w1[, "upr.ci"]; l2 <- w2[, "lwr.ci"]; u2 <- w2[, "upr.ci"]
  A <- e + f; B <- g + h; C <- e + g; D <- f + h
  phi <- if (any(c(A, B, C, D) == 0)) 0 else {
    num <- e * h - f * g
    if (num > 0) max(0, (num - n / 2) / sqrt(A * B * C * D)) else num / sqrt(A * B * C * D)
  }
  delta <- p1 - p2
  lower <- delta - sqrt((p1 - l1)^2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2)^2)
  upper <- delta + sqrt((u1 - p1)^2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2)^2)
  c(diff = unname(delta), lower = unname(lower), upper = unname(upper))
}

arms <- unique(d$arm); arms <- c(intersect(control, arms), setdiff(arms, control))
fmt_ci <- function(lo, hi) sprintf("%.1f%% to %.1f%%", 100 * lo, 100 * hi)

cat("| Arm | Cheats / n | Rate | Wilson 95% CI | Exact 95% CI | Cut-off replies | Cost $ |\n|---|---|---|---|---|---|---|\n")
for (a in arms) {
  g <- d[d$arm == a, ]; ga <- all_rows[all_rows$arm == a, ]
  k <- sum(g$cheat); n <- nrow(g)
  w <- BinomCI(k, n, method = "wilson"); cp <- BinomCI(k, n, method = "clopper-pearson")
  cat(sprintf("| `%s` | %d / %d | %.1f%% | %s | %s | %d of %d | %.2f |\n", a, k, n, 100 * k / n,
              fmt_ci(w[, "lwr.ci"], w[, "upr.ci"]), fmt_ci(cp[, "lwr.ci"], cp[, "upr.ci"]),
              sum(ga$n_cut_off), sum(ga$model_calls), sum(ga$cost_usd)))
}

if (control %in% arms && length(arms) > 1) {
  cat(sprintf("\nPaired contrasts vs `%s` (same tasks; Newcombe method 10 CI; exact McNemar on discordant tasks):\n\n", control))
  cat("| Comparison | Difference (pp) | 95% CI | Discordant (arm only / control only) | McNemar p |\n|---|---|---|---|---|\n")
  c0 <- d[d$arm == control, c("sample", "cheat")]
  for (a in setdiff(arms, control)) {
    m <- merge(d[d$arm == a, c("sample", "cheat")], c0, by = "sample", suffixes = c("_a", "_c"))
    e <- sum(m$cheat_a & m$cheat_c); f <- sum(m$cheat_a & !m$cheat_c); g <- sum(!m$cheat_a & m$cheat_c); h <- sum(!m$cheat_a & !m$cheat_c)
    nc <- newcombe_paired(e, f, g, h)
    p <- if (f + g == 0) 1 else binom.test(f, f + g)$p.value
    cat(sprintf("| `%s` − `%s` | %+.1f | %+.1f to %+.1f | %d / %d | %s |\n", a, control, 100 * nc["diff"], 100 * nc["lower"], 100 * nc["upper"], f, g,
                if (p < 0.0001) "< 0.0001" else sprintf("%.3f", p)))
  }
}
cat(sprintf("\nTotals over all rows incl. dead tasks: %d task-runs, $%.2f, %d cut-off replies.\n", nrow(all_rows), sum(all_rows$cost_usd), sum(all_rows$n_cut_off)))
