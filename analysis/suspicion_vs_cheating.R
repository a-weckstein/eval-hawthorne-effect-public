#!/usr/bin/env Rscript
# Does GLM-5.3-flash cheat less when it voices suspicion that the task is a test? ($0; reads result files only.)
#   Rscript analysis/suspicion_vs_cheating.R
# Output: results/2_hawthorne_effect/2026-10-22_suspicion_vs_cheating/ (tables CSV, results txt, figure PNG). Dead tasks excluded (D21).
# Two views (user question, 2026-10-22):
#  A. Per task (runs 1-3, hand labels): strongest unprompted remark over the task vs cheated in the loop. CONFOUNDED: a cheat
#     ends the loop early, so cheating tasks have fewer attempts in which to make a remark.
#  A2. Per attempt, same data as A (hand labels), each attempt reached counts once.
#  B. Per attempt (runs 1, 2 and the wording head-to-head; raw detector): for each attempt the task reached, was suspicion
#     voiced in the reasoning of this or any earlier attempt, and did this attempt cheat? Each attempt is a fair chance, so the
#     early-exit bias of A goes away. Remarks are in the reasoning, before the code of the same reply. Checked: no snippet is
#     from a reply after the first cheating attempt (reply index = attempt index).
# Models: lme4 glmer, task random intercept, arm (and run, attempt) as fixed effects. Intervals: task-cluster bootstrap.
suppressPackageStartupMessages({ library(ggplot2); library(scales); library(lme4) })
OUT <- "results/2_hawthorne_effect/2026-10-22_suspicion_vs_cheating"; dir.create(OUT, showWarnings = FALSE)
DEAD <- c("lcbhard_35", "lcbhard_87"); SURF <- "#fcfcfb"; INK <- "#0b0b0b"; INK2 <- "#52514e"; MUTED <- "#898781"; GRID <- "#e6e5e1"
RUNS <- c(run1 = "2026-10-14_glm_confirm_run1", run2 = "2026-10-18_glm_confirm_run2", run3 = "2026-10-21_glm_wording_h2h")
log_lines <- character(); say <- function(...) { l <- sprintf(...); cat(l, "\n"); log_lines <<- c(log_lines, l) }
boot_task <- function(task, y, B = 10000, seed = 20261022) { set.seed(seed); per <- tapply(y, task, function(x) c(sum(x), length(x)))
  k <- sapply(per, `[`, 1); n <- sapply(per, `[`, 2); m <- length(k)
  r <- replicate(B, { i <- sample.int(m, m, TRUE); sum(k[i]) / sum(n[i]) })
  data.frame(k = sum(y), n = length(y), rate = mean(y), lo = unname(quantile(r, .025)), hi = unname(quantile(r, .975))) }
arm_of <- function(t) sub("_paper.*$", "", sub("^.*canmod_", "", t))
smp <- do.call(rbind, lapply(names(RUNS), function(r) { s <- read.csv(file.path("results/2_hawthorne_effect", RUNS[[r]], "samples.csv")); s <- s[!s$sample %in% DEAD, ]
  data.frame(run = r, arm = s$arm, task = s$sample, attempts = s$attempts, cheat = as.integer(s$cheat_in_loop %in% c("True", "TRUE")),
             fpa = suppressWarnings(as.integer(s$first_pass_attempt))) }))
stopifnot(all(is.na(smp$fpa) == (smp$cheat == 0)), all(smp$fpa <= smp$attempts, na.rm = TRUE))
say("Episodes (task x arm x run): %d; cheated %d", nrow(smp), sum(smp$cheat))

# ---------- A. per task, runs 1-3, hand labels ----------
# Hand labels: run 1 by one reader (2026-10-18); runs 2-3 by Claude (2026-10-22), blind to prompt version, task and outcome. Pooled (user, 2026-10-22).
hl <- do.call(rbind, lapply(names(RUNS), function(r) { x <- read.csv(file.path("results/2_hawthorne_effect", RUNS[[r]], "eval_awareness_handlabels.csv"))
  x <- x[x$where == "reasoning" & !x$sample %in% DEAD, ]; data.frame(run = r, arm = x$arm, sample = x$sample, reply = x$reply, label = x$label) }))
hl$rank <- c(explicit = 2, trap_only = 1, false_alarm = 0)[hl$label]; stopifnot(!anyNA(hl$rank))
best <- aggregate(rank ~ run + arm + sample, hl, max)
a <- smp; a$hand <- best$rank[match(paste(a$run, a$arm, a$task), paste(best$run, best$arm, best$sample))]; a$hand[is.na(a$hand)] <- 0
LEV <- c("0" = "No remark", "1" = "Planted trap only", "2" = "Explicitly a test")
a$status <- factor(LEV[as.character(a$hand)], levels = LEV)
tA <- do.call(rbind, lapply(LEV, function(l) cbind(view = "A", status = l, boot_task(a$task[a$status == l], a$cheat[a$status == l]))))
say("\nA. Runs 1-3, per task, hand labels (all arms pooled; confounded by early exit):")
for (i in seq_len(nrow(tA))) say("  %-18s cheated %2d/%3d (%4.1f%%)  [%4.1f, %4.1f]", tA$status[i], tA$k[i], tA$n[i], 100 * tA$rate[i], 100 * tA$lo[i], 100 * tA$hi[i])
say("  By arm (cheated / tasks):"); for (ar in sort(unique(a$arm))) { x <- a[a$arm == ar, ]
  say("    %-18s %s", ar, paste(sprintf("%s %d/%d", c("none", "trap", "explicit"), tapply(x$cheat, x$status, sum), tapply(x$cheat, x$status, length)), collapse = "; ")) }
mA <- glmer(cheat ~ status + arm + run + (1 | task), a, family = binomial, nAGQ = 25, control = glmerControl(optimizer = "bobyqa"))
cA <- summary(mA)$coefficients; say("  glmer (task random intercept; arm, run fixed): OR trap vs none %.2f (p = %.3f); OR explicit vs none %.2f (p = %.3f)",
  exp(cA["statusPlanted trap only", 1]), cA["statusPlanted trap only", 4], exp(cA["statusExplicitly a test", 1]), cA["statusExplicitly a test", 4])

# ---------- A2. per attempt, runs 1-3, hand labels (same data as A, fair comparison) ----------
hr <- aggregate(reply ~ run + arm + sample + rank, hl[hl$rank > 0, ], min)   # first reply with each label level
ae <- do.call(rbind, lapply(seq_len(nrow(a)), function(i) { s <- a[i, ]; t <- seq_len(s$attempts)
  hx <- hr[hr$run == s$run & hr$arm == s$arm & hr$sample == s$task, ]; ft <- hx$reply[hx$rank == 1]; fe <- hx$reply[hx$rank == 2]
  lvl <- ifelse(length(fe) > 0 & t >= ifelse(length(fe), fe, Inf), 2, ifelse(length(ft) > 0 & t >= ifelse(length(ft), ft, Inf), 1, 0))
  data.frame(run = s$run, arm = s$arm, task = s$task, attempt = t, cheat_t = as.integer(!is.na(s$fpa) & s$fpa == t), lvl = lvl) }))
stopifnot(sum(ae$cheat_t) == sum(a$cheat), all(hr$reply <= 3))
ae$status <- factor(LEV[as.character(ae$lvl)], levels = LEV)
tA2 <- do.call(rbind, lapply(LEV, function(l) cbind(view = "A2", status = l, boot_task(ae$task[ae$status == l], ae$cheat_t[ae$status == l]))))
say("\nA2. Runs 1-3, per attempt, hand labels (strongest remark voiced in this or an earlier attempt): %d attempts", nrow(ae))
for (i in seq_len(nrow(tA2))) say("  %-18s cheated on %2d of %3d attempts (%4.1f%%)  [%4.1f, %4.1f]", tA2$status[i], tA2$k[i], tA2$n[i], 100 * tA2$rate[i], 100 * tA2$lo[i], 100 * tA2$hi[i])
mA2 <- glmer(cheat_t ~ status + factor(attempt) + arm + run + (1 | task), ae, family = binomial, nAGQ = 25, control = glmerControl(optimizer = "bobyqa"))
cA2 <- summary(mA2)$coefficients; say("  glmer (task random intercept; attempt, arm, run fixed): OR trap vs none %.2f (p = %.3f); OR explicit vs none %.2f (p = %.3f)",
  exp(cA2["statusPlanted trap only", 1]), cA2["statusPlanted trap only", 4], exp(cA2["statusExplicitly a test", 1]), cA2["statusExplicitly a test", 4])

# ---------- B. per attempt, runs 1-3, raw detector ----------
sn <- do.call(rbind, lapply(names(RUNS), function(r) { x <- read.csv(file.path("results/2_hawthorne_effect", RUNS[[r]], "eval_awareness_snippets.csv"))
  x <- x[x$where == "reasoning" & !x$sample %in% DEAD, ]; data.frame(run = r, arm = arm_of(x$task), task = x$sample, reply = x$reply) }))
first_rm <- aggregate(reply ~ run + arm + task, sn, min)
smp$first_remark <- first_rm$reply[match(with(smp, paste(run, arm, task)), with(first_rm, paste(run, arm, task)))]
stopifnot(all(is.na(smp$first_remark) | is.na(smp$fpa) | smp$first_remark <= smp$fpa))
b <- do.call(rbind, lapply(seq_len(nrow(smp)), function(i) { s <- smp[i, ]; t <- seq_len(s$attempts)
  data.frame(run = s$run, arm = s$arm, task = s$task, attempt = t, cheat_t = as.integer(!is.na(s$fpa) & s$fpa == t),
             susp = as.integer(!is.na(s$first_remark) & s$first_remark <= t)) }))
stopifnot(sum(b$cheat_t) == sum(smp$cheat))
say("\nB. Runs 1-3, per attempt (raw detector; suspicion voiced in this or an earlier attempt's reasoning): %d attempts", nrow(b))
tB <- do.call(rbind, lapply(c(0, 1), function(v) cbind(view = "B", status = c("No remark yet", "Suspicion voiced")[v + 1], boot_task(b$task[b$susp == v], b$cheat_t[b$susp == v]))))
for (i in seq_len(nrow(tB))) say("  %-17s cheated on %3d of %4d attempts (%4.1f%%)  [%4.1f, %4.1f]", tB$status[i], tB$k[i], tB$n[i], 100 * tB$rate[i], 100 * tB$lo[i], 100 * tB$hi[i])
say("  By attempt number (cheated/attempts, no remark | remark):")
for (t in 1:3) { x <- b[b$attempt == t, ]; say("    attempt %d: %d/%d | %d/%d", t, sum(x$cheat_t[x$susp == 0]), sum(x$susp == 0), sum(x$cheat_t[x$susp == 1]), sum(x$susp == 1)) }
mB <- glmer(cheat_t ~ susp + factor(attempt) + arm + run + (1 | task), b, family = binomial, nAGQ = 25, control = glmerControl(optimizer = "bobyqa"))
cB <- summary(mB)$coefficients; ciB <- exp(cB["susp", 1] + c(-1.96, 1.96) * cB["susp", 2])
say("  glmer (task random intercept; attempt, arm, run fixed): OR suspicion vs none %.2f [%.2f, %.2f], p = %.4f", exp(cB["susp", 1]), ciB[1], ciB[2], cB["susp", 4])
say("  Within arm (pooled runs; cheated/attempts, no remark | remark):")
for (ar in sort(unique(b$arm))) { x <- b[b$arm == ar, ]; say("    %-18s %d/%d (%4.1f%%) | %d/%d (%4.1f%%)", ar, sum(x$cheat_t[x$susp == 0]), sum(x$susp == 0), 100 * mean(x$cheat_t[x$susp == 0]),
  sum(x$cheat_t[x$susp == 1]), sum(x$susp == 1), 100 * mean(x$cheat_t[x$susp == 1])) }
writeLines(log_lines, file.path(OUT, "suspicion_vs_cheating_results.txt"))
tab <- rbind(tA, tA2, tB); write.csv(tab, file.path(OUT, "suspicion_vs_cheating.csv"), row.names = FALSE)

# ---------- figure ----------
# Layout (user, 2026-10-22): taller and narrower than the 16:9 deck pages (8.5 x 7.5 in), larger marks and y-axis text.
PANEL <- c(A = "A. Per task,\nhand-checked\n(biased by early exit)", A2 = "B. Per attempt,\nhand-checked\n(fair)", B = "C. Per attempt,\nraw detector\n(fair)")
tab$panel <- factor(PANEL[tab$view], levels = PANEL)
# Wording (user, 2026-10-22): "verbalized evaluation awareness"; labels say what GLM wrote, not what it believed.
YLAB <- c("No remark" = "No such\nremark", "Planted trap only" = "Says the\nconflict was\nplanted", "Explicitly a test" = "Says it's\nbeing tested", "Test or trap (detector)" = "Any awareness\nremark\n(detector)")
tab$key <- ifelse(tab$status == "No remark yet", "No remark", ifelse(tab$status == "Suspicion voiced", "Test or trap (detector)", tab$status))
tab$label <- factor(YLAB[tab$key], levels = rev(YLAB))
COL <- setNames(c(MUTED, "#86b6ef", "#184f95", "#3987e5"), YLAB)
tab$txt <- sprintf("%d/%d", tab$k, tab$n)
pf <- function(p) ifelse(p < 0.001, "p < 0.001", sprintf("p = %.2f", p))
orp <- function(cf, row) sprintf("%.2f (%s)", exp(cf[row, 1]), pf(cf[row, 4]))
p <- ggplot(tab, aes(y = label, x = rate)) +
  geom_segment(aes(x = lo, xend = hi, yend = label, colour = label), linewidth = 1.8, lineend = "round", alpha = 0.6) +
  geom_point(aes(fill = label), shape = 21, size = 6.2, stroke = 1.3, colour = SURF) +
  geom_text(aes(x = hi, label = txt), hjust = -0.15, size = 4.1, colour = INK2) +
  facet_wrap(~panel, nrow = 1, scales = "free_x") + scale_fill_manual(values = COL, guide = "none") + scale_colour_manual(values = COL, guide = "none") +
  scale_x_continuous(labels = percent_format(accuracy = 1), limits = c(0, NA), expand = expansion(mult = c(0, 0.55)),
                     breaks = function(lim) { b <- pretty(c(0, lim[2] / 1.55), 2); b[b <= lim[2] / 1.45] }) +   # ticks stay clear of the panel edge
  labs(title = "Only \"being tested\" remarks go with less\ncheating, and only weakly",
       subtitle = "GLM-5.3-flash, runs 1, 2 and the wording head-to-head, all prompt versions pooled.\nA: share of tasks that cheated. B and C: share of attempts that cheated, by the strongest\nunprompted awareness remark in that attempt's reasoning or earlier.",
       caption = paste0("Odds ratios vs no remark (mixed models: task random intercept; prompt version and run fixed;\nB and C also attempt). ",
                        "A: planted ", orp(cA, "statusPlanted trap only"), ", tested ", orp(cA, "statusExplicitly a test"), ".  B: planted ", orp(cA2, "statusPlanted trap only"),
                        ",\ntested ", orp(cA2, "statusExplicitly a test"), ".  C: any remark ", orp(cB, "susp"), ".\n",
                        "A looks like a strong link, but cheating stops the loop, so cheating tasks get fewer chances to\nvoice evaluation awareness. B and C give each attempt one chance. ",
                        "Axes differ: A counts tasks, B and C count attempts.\nEach remark comes before that attempt's code. Task-cluster bootstrap 95% intervals.\n",
                        "Hand labels (D22): run 1 by one reader; runs 2–3 by Claude, blind to prompt version and outcome.\nDetector counts include false alarms. ",
                        "Correlational only; the causal test is the reasoning-edit experiment.\nCode: analysis/suspicion_vs_cheating.R."),
       x = "Cheating rate (95% interval)", y = NULL) +
  theme_minimal(base_size = 13) + theme(
    plot.background = element_rect(fill = SURF, colour = NA), panel.background = element_rect(fill = SURF, colour = NA),
    text = element_text(colour = INK), axis.text = element_text(colour = INK2), axis.text.y = element_text(size = 15, colour = INK, lineheight = 1.0),
    axis.text.x = element_text(size = 11.5), axis.title = element_text(colour = INK2, size = 12),
    plot.title = element_text(face = "bold", size = 17, lineheight = 1.05), plot.subtitle = element_text(size = 11.5, colour = INK2, lineheight = 1.1),
    plot.caption = element_text(size = 9, colour = MUTED, hjust = 0, lineheight = 1.1), plot.caption.position = "plot", plot.title.position = "plot",
    panel.grid.major.y = element_blank(), panel.grid.minor = element_blank(), panel.grid.major.x = element_line(colour = GRID, linewidth = 0.4),
    strip.text = element_text(face = "bold", size = 11.5, hjust = 0, lineheight = 1.05), panel.spacing.x = unit(2.2, "lines"), plot.margin = margin(18, 22, 14, 18)) +
  coord_cartesian(clip = "off")
ggsave(file.path(OUT, "suspicion_vs_cheating.png"), p, width = 8.5, height = 7.5, dpi = 200, bg = SURF)
cat("wrote", OUT, "\n")
