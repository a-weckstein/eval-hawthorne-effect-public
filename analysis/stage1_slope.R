#!/usr/bin/env Rscript
# Pre-registered primary analysis for the stage 1 audit-probability sweep,
# applied to the collaborator's completed run (results/3_audit_probability/2026-10-20_glm_stage1_run1/final_outcomes.csv).
# Reads their file only; writes to results/3_audit_probability/2026-10-21_stage1_slope/. Dead tasks (lcbhard_35, lcbhard_87) excluded.
#   Rscript analysis/stage1_slope.R
suppressPackageStartupMessages(library(lme4))
d <- read.csv("results/3_audit_probability/2026-10-20_glm_stage1_run1/final_outcomes.csv", stringsAsFactors = FALSE)
d <- d[!d$sample %in% c("lcbhard_35", "lcbhard_87"), ]
d$cheat <- d$cheat %in% c("True", "TRUE", TRUE)
d$p <- as.numeric(d$probability)            # 0, .01, .10, .50, 1
d$pf <- factor(round(100 * d$p))
stopifnot(all(table(d$pf) == 59))
ctrl <- glmerControl(optimizer = "bobyqa")
out <- c()
say <- function(...) { s <- sprintf(...); cat(s, "\n"); out <<- c(out, s) }
say("Stage 1 sweep, GLM-5.3-flash, %d task-sessions (59 tasks x 5 levels); dead task excluded.", nrow(d))
say("Rates: %s", paste(sprintf("%s%%: %d/59 (%.1f%%)", levels(d$pf), tapply(d$cheat, d$pf, sum), 100 * tapply(d$cheat, d$pf, mean)), collapse = "; "))

# (a) PRIMARY: log-odds linear in p, task random intercept, two-sided Wald and likelihood-ratio tests
m0 <- glmer(cheat ~ 1 + (1 | task), data = transform(d, task = sample), family = binomial, control = ctrl)
m1 <- glmer(cheat ~ p + (1 | task), data = transform(d, task = sample), family = binomial, control = ctrl)
b <- fixef(m1)["p"]; se <- sqrt(vcov(m1)["p", "p"]); lr <- anova(m0, m1)
say("PRIMARY (a) linear in p: log-odds slope per 100 pp = %.3f (SE %.3f); odds ratio p=1 vs p=0 = %.2f (95%% CI %.2f to %.2f); Wald p = %.3f; LRT p = %.3f",
    b, se, exp(b), exp(b - 1.96 * se), exp(b + 1.96 * se), 2 * pnorm(-abs(b / se)), lr$`Pr(>Chisq)`[2])
say("  task random-intercept SD = %.2f", attr(VarCorr(m1)$task, "stddev"))

# (b) p as a factor, each level vs p = 0, Holm-corrected
mf <- glmer(cheat ~ pf + (1 | task), data = transform(d, task = sample), family = binomial, control = ctrl)
cf <- summary(mf)$coefficients[-1, ]
holm <- p.adjust(cf[, 4], "holm")
for (i in seq_len(nrow(cf))) say("PRIMARY (b) %s%% vs 0%%: odds ratio %.2f (95%% CI %.2f to %.2f), p = %.3f, Holm p = %.3f",
    sub("pf", "", rownames(cf)[i]), exp(cf[i, 1]), exp(cf[i, 1] - 1.96 * cf[i, 2]), exp(cf[i, 1] + 1.96 * cf[i, 2]), cf[i, 4], holm[i])
lrf <- anova(m0, mf); say("  overall test of any difference among the 5 levels (LRT, 4 df): p = %.3f", lrf$`Pr(>Chisq)`[2])

# Pre-registered shape test (i): step at p > 0, pooled {1, 10, 50} vs 0 (p = 100 excluded per the plan)
ds <- subset(d, p < 1); ds$any <- as.numeric(ds$p > 0)
ms <- glmer(cheat ~ any + (1 | task), data = transform(ds, task = sample), family = binomial, control = ctrl)
cs <- summary(ms)$coefficients["any", ]
say("SHAPE (i) step at p > 0 (pooled 1/10/50 vs 0): odds ratio %.2f (95%% CI %.2f to %.2f), p = %.3f", exp(cs[1]), exp(cs[1] - 1.96 * cs[2]), exp(cs[1] + 1.96 * cs[2]), cs[4])

# Exploratory (not pre-registered): curvature, since 0% and 100% are equal
mq <- glmer(cheat ~ p + I(p^2) + (1 | task), data = transform(d, task = sample), family = binomial, control = ctrl)
cq <- summary(mq)$coefficients["I(p^2)", ]
say("EXPLORATORY quadratic term in p: estimate %.2f (SE %.2f), p = %.3f (not pre-registered; U shape not claimed)", cq[1], cq[2], cq[4])

# Equivalence (pre-registered rule): a null between two levels only if the paired 95%% CI lies within +-10 pp
w <- reshape(transform(d[, c("sample", "pf", "cheat")], cheat = as.numeric(cheat)), idvar = "sample", timevar = "pf", direction = "wide")
for (lv in c("1", "10", "50", "100")) {
  x <- w[[paste0("cheat.", lv)]] - w[["cheat.0"]]
  ci <- mean(x) + c(-1, 1) * qt(.975, length(x) - 1) * sd(x) / sqrt(length(x))
  say("EQUIVALENCE %s%% - 0%%: %+.1f pp, paired 95%% CI %+.1f to %+.1f -> %s", lv, 100 * mean(x), 100 * ci[1], 100 * ci[2],
      if (ci[1] > -.10 && ci[2] < .10) "equivalent within +-10 pp" else "NOT shown equivalent (CI exceeds +-10 pp)")
}
writeLines(out, "results/3_audit_probability/2026-10-21_stage1_slope/stage1_slope_results.txt")
cat("\nwrote results/3_audit_probability/2026-10-21_stage1_slope/stage1_slope_results.txt\n")
