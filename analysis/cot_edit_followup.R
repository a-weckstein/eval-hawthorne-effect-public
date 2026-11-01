#!/usr/bin/env Rscript
# Insertion follow-up analysis (study_design_cot_edit.md section 14, D35). $0: reads result CSVs only.
#   Rscript analysis/cot_edit_followup.R [results/<date>_cot_edit_followup/samples.csv] [out_dir]
# Arms insert_real / insert_hedged are compared with the 2026-10-20 keep_at_point, insert and insert_control arms on the
# same 48 tasks; prompt_eval with the same tasks' fresh episodes in GLM runs 1 and 2 and with insert.
# Tests, as sections 11-13: mixed-effects logistic (lme4::glmer, task random intercept) and an exact sign test on
# task-level differences (2 samples per task per arm; a task counts "up"/"down" when its arm mean differs).
# --validate: instead reproduce section 11 (insert vs keep_at_point OR 0.06 (0.02-0.23); control OR 0.64 (0.32-1.30)).
suppressPackageStartupMessages(library(lme4))
args <- commandArgs(trailingOnly = TRUE)
validate <- "--validate" %in% args; args <- setdiff(args, "--validate")
COLS <- c("task", "arm", "rep", "error", "cheat", "cont", "cost", "src")
ins <- read.csv("results/4_cot_edits/2026-10-20_cot_edit_insertion/episodes_detail.csv", stringsAsFactors = FALSE)
if (is.null(ins$error)) ins$error <- 0  # that run had no errored episodes, so the column was not written
ins <- ins[ins$error == 0, ]; ins$src <- "insertion_2026-10-20"; ins <- ins[, COLS]
if (validate) { fu <- ins[0, ] } else {
  f <- if (length(args)) args[1] else "results/4_cot_edits/2026-10-22_cot_edit_followup/samples.csv"
  s <- read.csv(f, stringsAsFactors = FALSE); s <- s[!as.logical(s$error), ]
  fu <- data.frame(task = paste0(s$notice_arm, ":", s$sample), arm = s$arm, rep = s$rep, error = 0,
                   cheat = as.integer(as.logical(s$cheat)), cont = s$cont_chars, cost = s$cost_usd, src = "followup", stringsAsFactors = FALSE)[, COLS] }
fresh <- do.call(rbind, lapply(c(run1 = "results/2_hawthorne_effect/2026-10-14_glm_confirm_run1/samples.csv", run2 = "results/2_hawthorne_effect/2026-10-18_glm_confirm_run2/samples.csv"), function(f) {
  r <- read.csv(f, stringsAsFactors = FALSE); data.frame(task = paste0(r$arm, ":", r$sample), arm = "fresh_baseline", rep = NA, error = 0,
    cheat = as.integer(r$cheat_in_loop %in% c("True", "TRUE")), cont = NA, cost = r$cost_usd, src = basename(dirname(f)), stringsAsFactors = FALSE)[, COLS] }))
tasks <- unique(ins$task); fresh <- fresh[fresh$task %in% tasks, ]
d <- rbind(ins, fu, fresh)
stopifnot(length(unique(fresh$task)) == 48, nrow(fresh) == 96)

rate <- function(a) { x <- d[d$arm == a, ]; sprintf("%d/%d (%.0f%%)", sum(x$cheat), nrow(x), 100 * mean(x$cheat)) }
compare <- function(trt, ctl) {
  x <- d[d$arm %in% c(trt, ctl), ]; x$arm <- factor(x$arm, levels = c(ctl, trt))
  m <- tryCatch(glmer(cheat ~ arm + (1 | task), data = x, family = binomial, nAGQ = 25), error = function(e) NULL)
  or <- ci <- pz <- NA
  if (!is.null(m)) { b <- fixef(m)[2]; se <- sqrt(vcov(m)[2, 2]); or <- exp(b); ci <- exp(b + c(-1, 1) * 1.96 * se); pz <- 2 * pnorm(-abs(b / se)) }
  pt <- tapply(x$cheat, list(x$task, x$arm), mean); pt <- pt[complete.cases(pt), , drop = FALSE]
  dlt <- pt[, trt] - pt[, ctl]; up <- sum(dlt > 0); dn <- sum(dlt < 0)
  sp <- if (up + dn > 0) binom.test(up, up + dn)$p.value else NA
  data.frame(comparison = paste(trt, "vs", ctl), trt = rate(trt), ctl = rate(ctl), diff_pp = round(100 * (mean(d$cheat[d$arm == trt]) - mean(d$cheat[d$arm == ctl])), 1),
             tasks_up = up, tasks_down = dn, sign_p = signif(sp, 2), OR = round(or, 2), OR_lo = round(ci[1], 2), OR_hi = round(ci[2], 2), glmm_p = signif(pz, 2), n_tasks = nrow(pt)) }
if (validate) {
  res <- rbind(compare("insert", "keep_at_point"), compare("insert_control", "keep_at_point"), compare("insert", "insert_control"))
  print(res, row.names = FALSE); cat("\nExpected (section 11): insert vs keep OR 0.06 (0.02-0.23), 2 up / 22 down; control vs keep OR 0.64 (0.32-1.30), 8 up / 14 down; insert vs control OR 0.10 (0.03-0.38)\n")
  cat("fresh baseline on these 48 tasks:", rate("fresh_baseline"), "\n"); quit(status = 0) }
res <- rbind(compare("insert_real", "keep_at_point"), compare("insert_hedged", "keep_at_point"), compare("insert_real", "insert_control"),
             compare("insert_hedged", "insert"), compare("insert_real", "insert"), compare("prompt_eval", "fresh_baseline"), compare("prompt_eval", "insert"), compare("prompt_eval", "keep_at_point"))
print(res, row.names = FALSE)
cont <- aggregate(cont ~ arm, d[!is.na(d$cont), ], median); names(cont)[2] <- "median_reasoning_chars_after_edit"; print(cont, row.names = FALSE)
out <- if (length(args) > 1) args[2] else dirname(f); dir.create(out, showWarnings = FALSE, recursive = TRUE)
write.csv(res, file.path(out, "followup_tests.csv"), row.names = FALSE); write.csv(d[d$src == "followup", 1:7], file.path(out, "episodes_detail.csv"), row.names = FALSE)
cat("wrote", file.path(out, "followup_tests.csv"), "and episodes_detail.csv\n")
