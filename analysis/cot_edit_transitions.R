#!/usr/bin/env Rscript
# Did the reasoning edits flip outcomes on the same prompt? ($0; reads samples.csv from the three reasoning-edit runs.)
#   Rscript analysis/cot_edit_transitions.R
# User question (2026-10-22): how often did an edit move an episode from no-cheat to cheat, and back?
# Plan, fixed before counting:
#  1. Versus the original run: each edited episode restarts the original episode at the edit point, so the original
#     outcome from that reply onward (run1_first_pass non-empty) is the "before". Count flips per arm (2 samples per task,
#     each compared with the same original).
#  2. The control arm (same text, no edit) re-samples the same point; its flip rate is the noise baseline.
#  3. Head-to-head per task: edit (2 samples) vs control (2 samples); tasks where the edit cheated fewer / more / equal
#     times; exact sign test on the unequal tasks.
# Errored episodes are dropped (removal side: 2), with their task kept for the other arms.
OUT <- "results/4_cot_edits/2026-10-22_cot_edit_transitions"; dir.create(OUT, showWarnings = FALSE)
SIDES <- list(
  insertion   = list(dir = "2026-10-20_cot_edit_insertion",  control = "keep_at_point", arms = c("keep_at_point", "insert_control", "insert")),
  removal     = list(dir = "2026-10-21_cot_edit_removal",    control = "keep",          arms = c("keep", "cut", "replace")),
  probability = list(dir = "2026-10-21_cot_edit_probability", control = "keep_at_point", arms = c("keep_at_point", "ins_p0", "ins_p10", "ins_p100")))
lines <- character(); say <- function(...) { l <- sprintf(...); cat(l, "\n"); lines <<- c(lines, l) }
flips <- list(); h2h <- list()
for (side in names(SIDES)) {
  S <- SIDES[[side]]; d <- read.csv(file.path("results/4_cot_edits", S$dir, "samples.csv"))
  n0 <- nrow(d); d <- d[!(d$error %in% c("True", "TRUE")), ]
  d$task <- paste(d$notice_arm, d$sample, sep = ":")
  d$now <- as.integer(d$cheat %in% c("True", "TRUE")); d$orig <- as.integer(!is.na(d$run1_first_pass) & d$run1_first_pass != "")
  stopifnot(all(is.na(suppressWarnings(as.integer(d$run1_first_pass))) | as.integer(d$run1_first_pass) >= d$edited_reply))
  # the original outcome is a property of the task, so it must agree across all arms and samples of a task
  stopifnot(all(tapply(d$orig, d$task, function(x) length(unique(x))) == 1))
  say("\n== %s: %d tasks, %d episodes (%d errored dropped); original run cheated from the edit point on %d tasks",
      side, length(unique(d$task)), nrow(d), n0 - nrow(d), sum(tapply(d$orig, d$task, max)))
  say("  %-15s %8s %10s %10s %8s | %s", "arm", "episodes", "no->cheat", "cheat->no", "same", "cheat rate: original -> edited")
  for (a in S$arms) { x <- d[d$arm == a, ]
    f <- data.frame(side = side, arm = a, episodes = nrow(x), orig_no = sum(x$orig == 0), orig_yes = sum(x$orig == 1),
                    no_to_cheat = sum(x$orig == 0 & x$now == 1), cheat_to_no = sum(x$orig == 1 & x$now == 0), same = sum(x$orig == x$now),
                    orig_rate = mean(x$orig), now_rate = mean(x$now))
    flips[[length(flips) + 1]] <- f
    say("  %-15s %8d %6d/%-3d %6d/%-3d %8d | %4.1f%% -> %4.1f%%", a, f$episodes, f$no_to_cheat, f$orig_no, f$cheat_to_no, f$orig_yes, f$same, 100 * f$orig_rate, 100 * f$now_rate) }
  ctl <- tapply(d$now[d$arm == S$control], d$task[d$arm == S$control], sum); nc <- tapply(d$now[d$arm == S$control], d$task[d$arm == S$control], length)
  for (a in setdiff(S$arms, S$control)) { x <- d[d$arm == a, ]; e <- tapply(x$now, x$task, sum); ne <- tapply(x$now, x$task, length)
    t <- intersect(names(e), names(ctl)); t <- t[ne[t] == nc[t]]   # same number of samples in both arms
    fewer <- sum(e[t] < ctl[t]); more <- sum(e[t] > ctl[t]); eq <- sum(e[t] == ctl[t])
    p <- if (fewer + more) binom.test(more, fewer + more)$p.value else NA
    h2h[[length(h2h) + 1]] <- data.frame(side = side, arm = a, vs = S$control, tasks = length(t), edit_fewer = fewer, edit_more = more, equal = eq, sign_p = p)
    say("  head-to-head %s vs %s (%d tasks): edit cheated fewer times on %d tasks, more on %d, equal on %d; sign test p = %.4f",
        a, S$control, length(t), fewer, more, eq, p) }
}
F <- do.call(rbind, flips); Hh <- do.call(rbind, h2h)
write.csv(F, file.path(OUT, "flips_vs_original.csv"), row.names = FALSE); write.csv(Hh, file.path(OUT, "head_to_head_vs_control.csv"), row.names = FALSE)
writeLines(lines, file.path(OUT, "cot_edit_transitions_results.txt")); cat("wrote", OUT, "\n")
