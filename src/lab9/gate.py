"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from math import isfinite
from operator import gt, lt
from pathlib import Path
from statistics import mean

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def _loosened(current: dict, previous: dict) -> bool:
    for key, compare in (("min", lt), ("max", gt), ("max_increase", gt)):
        if key not in previous:
            continue
        value = current.get(key)
        if not isinstance(value, (int, float)) or not isfinite(value) or compare(value, previous[key]):
            return True
    return bool(previous.get("no_significant_drop") and not current.get("no_significant_drop"))


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    problems = []
    for collection, identity in (("metrics", ("id",)), ("slices", ("name", "metric"))):
        current = {tuple(entry[key] for key in identity): entry for entry in spec.get(collection, [])}
        for previous in base_spec.get(collection, []):
            key = tuple(previous[field] for field in identity)
            entry = current.get(key)
            if entry is None:
                problems.append(f"ratchet: removed {collection} {'/'.join(key)}")
                continue
            before = previous.get("threshold", {}) if collection == "metrics" else previous
            after = entry.get("threshold", {}) if collection == "metrics" else entry
            if (previous.get("blocking") and not entry.get("blocking")) or _loosened(after, before):
                problems.append(f"ratchet: loosened {collection} {'/'.join(key)}")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded_metrics = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
    row_metrics = set(graded_metrics) | {s["metric"] for s in spec.get("slices", [])}

    def coverage(report: dict, label: str) -> dict:
        rows = report["rows"]
        seeds = set(report["manifest"]["seeds"])
        items = {r["item_id"] for r in rows}
        index = {(r["item_id"], r["seed"]): frozenset(r.get("slices", [])) for r in rows}
        if (not seeds or not items or len(seeds) != len(report["manifest"]["seeds"])
                or len(items) != report["manifest"]["items"]
                or len(index) != len(rows)
                or index.keys() != {(item, seed) for item in items for seed in seeds}):
            problems.append(f"{label} does not contain exactly one row per item and seed")
        if report.get("evaluator_failures"):
            problems.append(f"{label} has evaluator failures")
        bad_rows = sum(any(r.get(m) not in (0, 1) for m in row_metrics) for r in rows)
        if bad_rows:
            problems.append(f"{label} has {bad_rows} rows with missing or invalid grades")
        metrics = report["metrics"]
        costs_valid = all(
            isinstance(r.get("cost"), (int, float)) and isfinite(r["cost"])
            for r in rows if "cost" in r or "cost_per_success" in metrics
        )
        if not costs_valid:
            problems.append(f"{label} has missing or non-finite trial costs")
        derived = aggregate(rows, graded_metrics, spec.get("pass_k", [])) if not bad_rows and costs_valid else {}
        for metric, value in metrics.items():
            if value is not None and (not isinstance(value, (int, float)) or not isfinite(value)):
                problems.append(f"{label} metric {metric} is not finite")
            elif metric in derived and value != derived[metric]:
                problems.append(f"{label} metric {metric} does not match the trial rows")
        return index

    pr_index, base_index = coverage(pr, "PR"), coverage(base, "baseline")
    if pr_index.keys() != base_index.keys():
        problems.append("PR item/seed coverage differs from baseline")
    elif pr_index != base_index:
        problems.append("PR slice tags differ from baseline")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems.extend(_ratchet(spec, base_spec))
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        if not a or a.keys() != b.keys():
            if rule.get("blocking"):
                blocked.append(sid)
            lines.append(f"  {sid:<36} missing paired slice grades")
            continue
        value = mean(a.values())
        failed = "min" in rule and value < rule["min"]
        note = ""
        if rule.get("no_significant_drop"):
            delta, lo, hi = _paired_ci(a, b, spec)
            failed = failed or hi < 0
            note = f" Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        verdict = "ok"
        if failed:
            verdict = "BLOCK" if rule.get("blocking") else "warn"
            if rule.get("blocking"):
                blocked.append(sid)
        lines.append(f"  {sid:<36} {value:.4f}{note} {verdict}")
    return blocked, lines


def _paired_ci(a: dict, b: dict, spec: dict) -> tuple[float, float, float]:
    keys = sorted(a.keys() & b.keys())
    bs = spec.get("bootstrap", {})
    return stats.paired_bootstrap(
        [a[k] for k in keys], [b[k] for k in keys],
        n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
        confidence=bs.get("confidence", 0.95),
    )


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            d, lo, hi = _paired_ci(a, b, spec)
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
