"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

import numpy as np
from scipy.stats import bootstrap

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    counts = dict.fromkeys(("tp", "fp", "fn", "tn"), 0)
    for expected, observed in zip(human, judge, strict=True):
        if expected not in ("PASS", POS) or observed not in ("PASS", POS):
            raise ValueError("judge labels must be PASS or FAIL")
        key = ("t" if observed == expected else "f") + ("p" if observed == POS else "n")
        counts[key] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    counts = confusion(human, judge)
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
    return (tp / (tp + fp) if tp + fp else 0.0,
            tp / (tp + fn) if tp + fn else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    counts = confusion(human, judge)
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    n = sum(counts.values())
    chance = (tp + fp) * (tp + fn) + (tn + fp) * (tn + fn)
    if chance == n * n:
        raise ValueError("kappa is undefined")
    return ((tp + tn) * n - chance) / (n * n - chance)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    signal = sensitivity + specificity - 1
    if signal <= 0:
        raise ValueError("Rogan–Gladen requires sensitivity + specificity > 1")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / signal))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    pr, base = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if pr.ndim != 1 or pr.shape != base.shape or not pr.size:
        raise ValueError("paired bootstrap requires equally sized, nonempty vectors")
    if not (np.isfinite(pr).all() and np.isfinite(base).all()):
        raise ValueError("paired bootstrap requires finite values")
    differences = pr - base
    delta = float(differences.mean())
    if np.all(differences == differences[0]):
        return delta, delta, delta
    ci = bootstrap(
        (pr, base), lambda a, b, axis: np.mean(a - b, axis=axis),
        paired=True, method="percentile", n_resamples=n_resamples,
        rng=np.random.default_rng(rng), confidence_level=confidence,
    ).confidence_interval
    return delta, float(ci.low), float(ci.high)


def _validate_pass_counts(n: int, c: int, k: int) -> None:
    if not all(type(value) is int for value in (n, c, k)) or not (0 <= c <= n and 1 <= k <= n):
        raise ValueError("pass counts require integers with 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_counts(n, c, k)
    return 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_counts(n, c, k)
    return comb(c, k) / comb(n, k)
