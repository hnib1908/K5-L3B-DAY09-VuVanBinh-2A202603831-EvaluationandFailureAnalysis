"""Regression tests for the trace cases used in the eval card."""
import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize(
    "claim,grader_name,seeded_amount,fixed_amount",
    [("C-002", "DbFactKept", 20000, 0), ("C-008", "ReplyMatchesLedger", 20000, 20000)],
)
def test_grader_distinguishes_regression_from_fixed(claim, grader_name, seeded_amount, fixed_amount):
    from pydantic_evals.evaluators import EvaluatorContext

    from lab9 import graders
    from lab9.trace_case import investigate

    bad = investigate("seeded_regression", claim, 11)["trial"]
    good = investigate("fixed", claim, 11)["trial"]
    assert bad["snapshot"]["refund_vnd"] == seeded_amount
    assert good["snapshot"]["refund_vnd"] == fixed_amount
    grader = getattr(graders, grader_name)()
    for name, trial, expected in (("seeded", bad, False), ("fixed", good, True)):
        context = EvaluatorContext(name=name, inputs={}, metadata=None, expected_output=None,
                                   output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})
        assert grader.evaluate(context).value is expected
