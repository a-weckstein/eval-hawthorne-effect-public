"""Marginal ML for the planned logistic task-random-intercept probability slope.

Requires numpy/scipy in an isolated analysis environment. Integrates the scalar
Gaussian random effect by fixed Gauss-Hermite quadrature, with analytic score and
observed Hessian. Checks derivatives and agreement at 80/160/320 nodes. No API
calls. Original-study artifacts are never overwritten.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import scipy
from numpy.polynomial.hermite import hermgauss
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import expit, logsumexp
from scipy.stats import chi2, norm

PROBS = np.array([0, .01, .1, .5, 1.])
OUT = Path('results/3_audit_probability/2026-10-21_glm_stage1_primary_analysis')


class Likelihood:
    def __init__(self, y, nodes):
        self.y = y
        x, w = hermgauss(nodes)
        self.z = np.sqrt(2)*x
        self.log_weights = np.log(w)-.5*np.log(np.pi)

    def evaluate(self, theta, hessian=False):
        alpha, beta, log_sd = theta
        u = np.exp(log_sd)*self.z
        eta = alpha+beta*PROBS[None, :]+u[:, None]
        mu = expit(eta)
        node_ll = (self.y[:, None, :]*eta[None, :, :]-np.logaddexp(0, eta)[None, :, :]).sum(axis=2)
        weighted = node_ll+self.log_weights[None, :]
        ll = logsumexp(weighted, axis=1)
        posterior = np.exp(weighted-ll[:, None])
        design = np.stack([np.ones_like(eta), np.broadcast_to(PROBS, eta.shape),
                           np.broadcast_to(u[:, None], eta.shape)], axis=2)
        residual = self.y[:, None, :]-mu[None, :, :]
        g = np.einsum('nkj,kjd->nkd', residual, design)
        score = np.einsum('nk,nkd->nd', posterior, g)
        if not hessian:
            return -float(ll.sum()), -score.sum(axis=0)
        complete_h = -np.einsum('kj,kjd,kje->kde', mu*(1-mu), design, design)
        marginal_h = np.einsum('nk,kde->nde', posterior, complete_h)
        marginal_h[:, 2, 2] += (posterior*residual.sum(axis=2)*u[None, :]).sum(axis=1)
        marginal_h += np.einsum('nk,nkd,nke->nde', posterior, g, g)
        marginal_h -= np.einsum('nd,ne->nde', score, score)
        return -float(ll.sum()), -score.sum(axis=0), -marginal_h.sum(axis=0)


def load(path):
    rows = [r for r in csv.DictReader(path.open()) if r['sample'] not in ('lcbhard_35', 'lcbhard_87')]
    ids = sorted({r['sample'] for r in rows}, key=lambda s: int(s.split('_')[1]))
    d = {(r['sample'], r['arm']): float(r['cheat'] == 'True') for r in rows}
    assert len(d) == len(rows) == len(ids)*5
    return np.array([[d[sid, f'audit_{p}'] for p in (0, 1, 10, 50, 100)] for sid in ids])


def fit(y, label):
    estimates = []
    derivative_errors = {}
    for nodes in (80, 160, 320):
        model = Likelihood(y, nodes)
        test = np.array([-1.8, -.3, -.4])
        step = 1e-5
        basis = np.eye(3)*step
        numeric_g = np.array([(model.evaluate(test+b)[0]-model.evaluate(test-b)[0])/(2*step) for b in basis])
        numeric_h = np.column_stack([(model.evaluate(test+b)[1]-model.evaluate(test-b)[1])/(2*step) for b in basis])
        _, analytical_g, analytical_h = model.evaluate(test, True)
        assert np.allclose(numeric_g, analytical_g, atol=1e-6, rtol=1e-5)
        assert np.allclose(numeric_h, analytical_h, atol=1e-5, rtol=1e-5)
        derivative_errors[nodes] = dict(gradient_max_abs=float(np.max(abs(numeric_g-analytical_g))),
                                       hessian_max_abs=float(np.max(abs(numeric_h-analytical_h))))
        starts = [(-2, 0, -.5), (-2, -.5, 0), (-2, .5, -2)]
        fits = [minimize(model.evaluate, start, jac=True, method='L-BFGS-B',
                         bounds=[(-30, 20), (-30, 30), (-12, 4)],
                         options=dict(ftol=1e-14, gtol=1e-8, maxiter=2000)) for start in starts]
        best = min(fits, key=lambda result: result.fun)
        assert best.success, best.message
        value, gradient, h = model.evaluate(best.x, True)
        assert np.max(abs(gradient)) < 1e-4
        estimates.append(dict(nodes=nodes, theta=best.x.tolist(), negative_loglik=value,
                              gradient_max_abs=float(np.max(abs(gradient)))))
    assert max(abs(estimates[-1]['theta'][1]-e['theta'][1]) for e in estimates) < 1e-5
    assert max(abs(estimates[-1]['negative_loglik']-e['negative_loglik']) for e in estimates) < 1e-5
    model = Likelihood(y, 320)
    theta = np.array(estimates[-1]['theta'])
    value, gradient, h = model.evaluate(theta, True)
    covariance = np.linalg.pinv(h, rcond=1e-10)
    se = float(np.sqrt(covariance[1, 1]))
    beta = float(theta[1])
    sd = float(np.exp(theta[2]))
    def null_objective(x):
        value, g = model.evaluate([x[0], 0, x[1]])
        return value, g[[0, 2]]
    null = minimize(null_objective, [theta[0], theta[2]], jac=True, method='L-BFGS-B',
                    bounds=[(-30, 20), (-12, 4)], options=dict(ftol=1e-14, gtol=1e-8, maxiter=2000))
    assert null.success
    lr = max(0., 2*(null.fun-value))
    # Independent adaptive integration and derivative-free optimization checks.
    integrated_ll = 0.
    for outcomes in y:
        def integrand(z):
            eta = theta[0]+theta[1]*PROBS+sd*z
            logp = np.sum(outcomes*eta-np.logaddexp(0, eta))-.5*z*z-.5*np.log(2*np.pi)
            return np.exp(logp)
        integral, _ = quad(integrand, -np.inf, np.inf, epsabs=1e-12, epsrel=1e-10)
        integrated_ll += np.log(integral)
    assert abs(integrated_ll+value) < 1e-7
    independent = minimize(lambda t: model.evaluate(t)[0], theta+np.array([.1, -.1, .1]),
                           method='Nelder-Mead', bounds=[(-30, 20), (-30, 30), (-12, 4)],
                           options=dict(xatol=1e-9, fatol=1e-10, maxiter=2000))
    assert independent.success and abs(independent.fun-value) < 1e-7
    assert abs(independent.x[1]-theta[1]) < 1e-5
    return dict(label=label, formula='cheat ~ probability + (1 | task)', probability_scale='fraction 0 to 1',
        tasks=len(y), observations=int(y.size), method='marginal maximum likelihood, 320-node fixed Gauss-Hermite quadrature',
        inference_note='Two-sided Wald slope test; likelihood-ratio sensitivity also reported. Numerical method finalized after collection; no outcome-based sample changes.',
        intercept=float(theta[0]), beta=beta, beta_se=se, beta_wald_95=[beta-1.95996398454*se, beta+1.95996398454*se],
        wald_z=beta/se, wald_p=float(2*norm.sf(abs(beta/se))),
        random_intercept_sd=sd, random_variance_near_boundary=sd < .001,
        odds_ratio_per_10_percentage_points=float(np.exp(.1*beta)),
        odds_ratio_per_10pp_wald_95=np.exp(.1*np.array([beta-1.95996398454*se, beta+1.95996398454*se])).tolist(),
        negative_loglik=value, likelihood_ratio_statistic=lr, likelihood_ratio_p=float(chi2.sf(lr, 1)),
        numerical_checks=dict(derivative_checks=derivative_errors, quadrature_fits=estimates,
                              hessian_eigenvalues=np.linalg.eigvalsh(h).tolist(),
                              adaptive_integral_loglik_difference=float(integrated_ll+value),
                              derivative_free_optimizer_beta_difference=float(independent.x[1]-theta[1])),
        software=dict(numpy=np.__version__, scipy=scipy.__version__),
        method_reference='https://lme4.github.io/lme4/reference/glmer.html',
        limitation='A linear slope does not test every nonmonotonic shape. Original model/task slice only; extension and pooled fits are exploratory.')


def main():
    OUT.mkdir(exist_ok=True)
    cohorts = (
      ('original_primary', Path('results/3_audit_probability/2026-10-20_glm_stage1_run1/final_outcomes.csv'), 'Original preplanned 59-task study: primary estimand'),
      ('extension_exploratory', Path('results/3_audit_probability/2026-10-21_glm_stage1_extension/final_outcomes.csv'), 'Post-outcome extension: exploratory'),
      ('pooled_exploratory', Path('results/3_audit_probability/2026-10-21_glm_stage1_pooled_exploratory/final_outcomes.csv'), 'Post-outcome pool: exploratory'))
    for name, source, label in cohorts:
        if not source.exists():
            continue
        result = fit(load(source), label)
        result['source'] = str(source)
        result['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        (OUT/f'{name}.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: result[k] for k in ('label', 'beta', 'beta_se', 'wald_p', 'likelihood_ratio_p', 'random_intercept_sd')}))


if __name__ == '__main__':
    main()
