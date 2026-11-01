# Planned primary slope: later analysis supplement

The original 59-task study is the confirmatory cohort for the planned estimand `cheat ~ probability + (1 | task)`, with probability as a fraction from 0 to 1. Extension and pooled fits below are explicitly exploratory because the extension was selected after viewing outcomes.

| Cohort | Tasks | Slope beta | SE | Wald 95% CI | Two-sided Wald p | LR sensitivity p |
|---|---:|---:|---:|---:|---:|---:|
| Original preplanned 59-task study: primary estimand | 59 | 0.2319 | 0.4619 | -0.6735 to 1.1373 | 0.6157 | 0.6177 |
| Post-outcome extension: exploratory | 42 | -0.1157 | 0.7655 | -1.6160 to 1.3847 | 0.8799 | 0.8794 |
| Post-outcome pool: exploratory | 101 | 0.1367 | 0.3945 | -0.6366 to 0.9100 | 0.7289 | 0.7299 |

Method: a Python marginal maximum-likelihood implementation of the specified binomial-logit Gaussian task-random-intercept model. Scalar random effects are integrated with 320-node fixed Gauss-Hermite quadrature. This is not an execution of R/lme4; its [GLMM documentation](https://lme4.github.io/lme4/reference/glmer.html) describes the model and role of random-effect integration. The numerical implementation and Wald inference were finalized after collection; the earlier plan fixed the estimand/model but not a specific fitting implementation.

Checks: analytic gradients/Hessians against finite differences; stable estimates and log likelihood at 80/160/320 nodes; multiple optimization starts; independent adaptive integration and derivative-free optimizer agreement. Exact errors, convergence diagnostics, source hashes and NumPy/SciPy versions are in each JSON. The fitting environment is isolated from the experiment runtime.

A linear slope does not test every step or U-shaped alternative. The likelihood-ratio check is a sensitivity analysis, not a second selected primary test. These are one-model/one-host results with substantial task and run uncertainty. No sample-size change or stopping decision was based on these tests.

Reproduce with `python analysis/fit_stage1_glmm.py` in an environment containing NumPy/SciPy. JSON files: [original primary](original_primary.json), [extension exploratory](extension_exploratory.json), [pooled exploratory](pooled_exploratory.json). Original-study artifacts were not overwritten.
