"""Node 6: Analyze test failures and suggest/apply fixes."""
from agents.llm import PROJECT_ROOT, get_llm, strip_fences, text_of


def suggest_fix(state: dict) -> dict:
    """Read failure output, produce corrected test file."""
    test_stdout = state["test_stdout"]
    test_code = state["test_code"]
    exploration = state.get("app_exploration", "")
    feedback = state.get("fix_feedback", "")

    prompt = f"""You are a Playwright debugging expert for https://www.saucedemo.com/.

CURRENT TEST CODE:
```typescript
{test_code}
```

FAILURE OUTPUT:
```
{test_stdout}
```

REAL PAGE SELECTORS (from Playwright MCP exploration):
{exploration}

HUMAN FEEDBACK ON A PREVIOUS FIX (apply it if present): {feedback or "none"}

Known gotchas on saucedemo.com:
- Error messages include "Epic sadface: " prefix
- Cart badge element doesn't exist when cart is empty (0 items)
- After login the URL is exactly https://www.saucedemo.com/inventory.html
- data-test attributes are the most reliable selectors
- The site is a React SPA — wait for navigation with waitForURL
- Visiting /inventory.html without a session does NOT redirect: the URL stays /inventory.html,
  the login form renders, and [data-test="error"] shows
  "Epic sadface: You can only access '/inventory.html' when you are logged in."

Diagnose each failure and output the COMPLETE corrected test file.
No markdown fences. No explanations. Just the fixed TypeScript code.
"""

    code = strip_fences(text_of(get_llm().invoke(prompt)))

    return {
        "fix_suggestion": code,
        "current_node": "fix_agent",
        "status": "waiting_human",
        "event_log": state.get("event_log", []) + [
            {"node": "fix_agent", "event": "completed",
             "summary": f"Fix suggested (retry {state.get('retry_count', 0) + 1}/{state.get('max_retries', 2)})"}
        ],
    }


def apply_fix(state: dict) -> dict:
    """Write the approved fix to disk."""
    fix_code = state["fix_suggestion"]
    (PROJECT_ROOT / "tests" / "swag-labs.spec.ts").write_text(fix_code, encoding="utf-8")

    return {
        "test_code": fix_code,
        "retry_count": state.get("retry_count", 0) + 1,
        "current_node": "apply_fix",
        "event_log": state.get("event_log", []) + [
            {"node": "apply_fix", "event": "completed", "summary": "Fix applied — re-running tests"}
        ],
    }
