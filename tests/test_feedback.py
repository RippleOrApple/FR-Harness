from fr_harness.feedback import parse_pytest_result


def test_parse_pytest_failure_extracts_failed_node_id() -> None:
    feedback = parse_pytest_result(
        1,
        "FAILED test_app.py::test_greeting - AssertionError\n1 failed in 0.02s\n",
        "",
    )

    assert feedback.passed is False
    assert feedback.failed_tests == ["test_app.py::test_greeting"]
    assert "AssertionError" in feedback.summary


def test_parse_pytest_only_accepts_zero_and_combines_streams() -> None:
    feedback = parse_pytest_result(2, "collection output", "collection error")

    assert feedback.passed is False
    assert feedback.summary == "collection output\ncollection error"


def test_parse_pytest_summary_is_limited_to_2000_characters() -> None:
    feedback = parse_pytest_result(0, "x" * 2_500, "")

    assert feedback.passed is True
    assert len(feedback.summary) == 2_000

