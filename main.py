#!/usr/bin/env python3
"""
QA Agent Orchestration — CLI with human-in-the-loop.
Sends SSE events to dashboard at http://localhost:8500.

    python main.py                     # interactive review at every gate
    python main.py --auto-approve      # approve every gate (unattended run)
"""
import argparse
import os
import sys
import uuid

import httpx

# Windows consoles default to cp1252; the CLI prints emoji and Playwright output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.llm import MODEL  # noqa: E402  (also loads the .env files)
from agents.graph import build_graph  # noqa: E402
from agents.gap_analyzer import analyze_gaps  # noqa: E402
from agents.bdd_generator import generate_bdd  # noqa: E402
from agents.test_generator import generate_tests  # noqa: E402
from agents.fix_agent import suggest_fix  # noqa: E402

DASHBOARD_URL = "http://localhost:8500"

DEFAULT_REQUIREMENT = (
    "Add end-to-end test coverage for the complete purchase flow on Swag Labs — "
    "login with standard_user/secret_sauce, add Sauce Labs Backpack to cart, "
    "checkout with shipping info, and verify order confirmation"
)

# Which state field each node's output lives in (shown in the dashboard detail panel)
DETAIL_KEYS = {
    "gap_analyzer": "gap_analysis",
    "bdd_generator": "bdd_scenarios",
    "app_explorer": "app_exploration",
    "test_generator": "test_code",
    "test_runner": "test_stdout",
    "fix_agent": "fix_suggestion",
    "apply_fix": "test_code",
}

# Gate (node interrupted before) → what the human reviews, and how a rejection regenerates it
GATES = {
    "generate_bdd": dict(review="gap_analysis", label="📋 GAP ANALYSIS",
                         approved="gap_approved", feedback="gap_feedback",
                         regen=("analyze_gaps", analyze_gaps)),
    "explore_app": dict(review="bdd_scenarios", label="📋 BDD SCENARIOS",
                        approved="bdd_approved", feedback="bdd_feedback",
                        regen=("generate_bdd", generate_bdd)),
    "run_tests": dict(review="test_code", label="📋 GENERATED TESTS",
                      approved="test_approved", feedback="test_feedback",
                      regen=("generate_tests", generate_tests)),
    "apply_fix": dict(review="fix_suggestion", label="🔧 SUGGESTED FIX",
                      approved="fix_approved", feedback="fix_feedback",
                      regen=("suggest_fix", suggest_fix)),
}


def send_event(event_type: str, data: dict):
    try:
        httpx.post(f"{DASHBOARD_URL}/api/event", json={"type": event_type, **data}, timeout=2)
    except Exception:
        pass


def publish_new_events(state: dict, seen: int) -> int:
    """Print and forward every event_log entry added since the last call."""
    log = state.get("event_log", [])
    for entry in log[seen:]:
        node = entry["node"]
        print(f"\n✔ {node}: {entry.get('summary', '')}")
        key = DETAIL_KEYS.get(node)
        send_event("node_update", {
            "node": node,
            "summary": entry.get("summary", ""),
            "status": state.get("status", ""),
            "test_passed": state.get("test_passed"),
            "retry_count": state.get("retry_count", 0),
            "details": (state.get(key) or "")[:20000] if key else "",
        })
    return len(log)


def human_review(gate_name: str, state: dict, auto_approve: bool) -> tuple[bool, str]:
    gate = GATES[gate_name]
    print("\n" + "=" * 60)
    print(f"  🔍 HUMAN REVIEW — before {gate_name.upper()}")
    print("=" * 60)

    content = state.get(gate["review"], "")
    if content:
        print(f"\n{gate['label']}:\n")
        print(content[:3000])
        if len(content) > 3000:
            print(f"\n... ({len(content) - 3000} more chars — full text in the dashboard)")

    print("\n" + "-" * 40)
    if auto_approve:
        print("  ✅ Auto-approved (--auto-approve)")
        return True, ""

    choice = input("  [A]pprove / [R]eject with feedback / [Q]uit: ").strip().lower()
    if choice == "q":
        send_event("aborted", {"node": gate_name})
        print("\n🛑 Aborted by reviewer.")
        sys.exit(0)
    if choice.startswith("r"):
        return False, input("  Your feedback: ").strip()
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="QA Agent Orchestration — Swag Labs demo")
    parser.add_argument("--requirement", help="Requirement text (skips the prompt)")
    parser.add_argument("--auto-approve", action="store_true", help="Approve every human gate")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not found.")
        print("   Looked in the environment, ./.env and ../ai-test-architect/.env")
        sys.exit(1)

    print("\n🤖 QA Agent Orchestration Demo")
    print("   Target: https://www.saucedemo.com/")
    print(f"   Model:  {MODEL}")
    print("=" * 50)

    requirement = args.requirement
    if not requirement and not args.auto_approve:
        requirement = input("\nEnter requirement (or press Enter for default):\n> ").strip()
    requirement = requirement or DEFAULT_REQUIREMENT

    print(f"\n📝 {requirement}\n")
    send_event("start", {"requirement": requirement, "model": MODEL})

    app = build_graph()
    config = {"configurable": {"thread_id": f"demo-{uuid.uuid4().hex[:8]}"}}

    graph_input = {
        "requirement": requirement,
        "gap_analysis": "", "retrieved_docs": [],
        "gap_approved": None, "gap_feedback": "",
        "bdd_scenarios": "", "bdd_approved": None, "bdd_feedback": "",
        "app_exploration": "",
        "test_code": "", "test_approved": None, "test_feedback": "",
        "test_stdout": "", "test_passed": None, "allure_report_path": "",
        "fix_suggestion": "", "fix_approved": None, "fix_feedback": "",
        "retry_count": 0, "max_retries": 2,
        "current_node": "", "status": "in_progress", "event_log": [],
    }
    seen = 0

    while True:
        for values in app.stream(graph_input, config, stream_mode="values"):
            seen = publish_new_events(values, seen)
        graph_input = None  # every later stream resumes from the checkpoint

        snapshot = app.get_state(config)
        if not snapshot.next:
            break

        gate_name = snapshot.next[0]
        gate = GATES[gate_name]
        send_event("waiting_human", {"node": gate_name})

        approved, feedback = human_review(gate_name, snapshot.values, args.auto_approve)
        send_event("human_decision", {"node": gate_name, "approved": approved, "feedback": feedback})

        if approved:
            update = {gate["approved"]: True}
            if feedback:
                update[gate["feedback"]] = feedback
            app.update_state(config, update)
        else:
            # Re-run the node that produced the artifact, with the reviewer's feedback.
            # Writing as that node keeps the graph paused at the same gate for re-review.
            regen_node, regen_fn = gate["regen"]
            print(f"\n↻ Regenerating via {regen_node} with your feedback...")
            result = regen_fn({**snapshot.values, gate["feedback"]: feedback})
            result.update({gate["approved"]: False, gate["feedback"]: feedback})
            app.update_state(config, result, as_node=regen_node)
            seen = publish_new_events(app.get_state(config).values, seen)

    final = app.get_state(config).values
    print("\n" + "=" * 60)
    if final.get("test_passed"):
        print("  ✅ ALL 5 TESTS PASSED")
    else:
        print("  ❌ PIPELINE COMPLETED WITH FAILURES")
    if final.get("allure_report_path"):
        print(f"  📊 Report: {final['allure_report_path']}  (also at {DASHBOARD_URL}/allure/)")
    print("=" * 60)
    send_event("complete", {
        "test_passed": bool(final.get("test_passed")),
        "retry_count": final.get("retry_count", 0),
        "allure": bool(final.get("allure_report_path")),
    })


if __name__ == "__main__":
    main()
