from typing import TypedDict, Literal, Optional


class QAState(TypedDict):
    requirement: str
    # Node 1 output
    gap_analysis: str
    retrieved_docs: list[str]
    gap_approved: Optional[bool]
    gap_feedback: str
    # Node 2 output
    bdd_scenarios: str
    bdd_approved: Optional[bool]
    bdd_feedback: str
    # Node 3 output
    app_exploration: str
    # Node 4 output
    test_code: str
    test_approved: Optional[bool]
    test_feedback: str
    # Node 5 output
    test_stdout: str
    test_passed: Optional[bool]
    allure_report_path: str
    # Node 6 output
    fix_suggestion: str
    fix_approved: Optional[bool]
    fix_feedback: str
    # Control
    retry_count: int
    max_retries: int
    current_node: str
    status: Literal["pending", "in_progress", "waiting_human", "passed", "failed", "aborted"]
    event_log: list[dict]
