"""
QA Agent Orchestration — LangGraph state machine.

Flow:
  requirement → gap_analyzer → [HUMAN] → bdd_generator → [HUMAN]
  → app_explorer → test_generator → [HUMAN] → test_runner
  → (if fail) fix_agent → [HUMAN] → apply_fix → [HUMAN] → test_runner (max 2 retries)
  → (if pass) DONE

Each [HUMAN] gate is an interrupt_before on the node that consumes the artifact
under review. main.py handles approve (resume) and reject (regenerate with feedback).
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.app_explorer import explore_app
from agents.bdd_generator import generate_bdd
from agents.fix_agent import apply_fix, suggest_fix
from agents.gap_analyzer import analyze_gaps
from agents.state import QAState
from agents.test_generator import generate_tests
from agents.test_runner import run_tests

# Gate name (node interrupted before) → artifact the human reviews there
HUMAN_GATES = ["generate_bdd", "explore_app", "run_tests", "apply_fix"]


def route_after_test(state: QAState) -> str:
    if state.get("test_passed"):
        return "done"
    if state.get("retry_count", 0) >= state.get("max_retries", 2):
        return "done"
    return "suggest_fix"


def build_graph():
    graph = StateGraph(QAState)

    graph.add_node("analyze_gaps", analyze_gaps)
    graph.add_node("generate_bdd", generate_bdd)
    graph.add_node("explore_app", explore_app)
    graph.add_node("generate_tests", generate_tests)
    graph.add_node("run_tests", run_tests)
    graph.add_node("suggest_fix", suggest_fix)
    graph.add_node("apply_fix", apply_fix)

    graph.set_entry_point("analyze_gaps")
    graph.add_edge("analyze_gaps", "generate_bdd")
    graph.add_edge("generate_bdd", "explore_app")
    graph.add_edge("explore_app", "generate_tests")
    graph.add_edge("generate_tests", "run_tests")

    graph.add_conditional_edges("run_tests", route_after_test, {
        "suggest_fix": "suggest_fix",
        "done": END,
    })

    graph.add_edge("suggest_fix", "apply_fix")
    graph.add_edge("apply_fix", "run_tests")

    return graph.compile(checkpointer=MemorySaver(), interrupt_before=HUMAN_GATES)
