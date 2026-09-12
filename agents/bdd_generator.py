"""Node 2: Generate BDD Gherkin scenarios from approved gaps."""
from agents.llm import PROJECT_ROOT, get_llm, strip_fences, text_of


def generate_bdd(state: dict) -> dict:
    """Generate Gherkin .feature content targeting saucedemo.com."""
    requirement = state["requirement"]
    gap_analysis = state["gap_analysis"]
    gap_feedback = state.get("gap_feedback", "")
    bdd_feedback = state.get("bdd_feedback", "")

    prompt = f"""You are a BDD test architect for the Swag Labs app (https://www.saucedemo.com/).

REQUIREMENT: {requirement}

GAP ANALYSIS:
{gap_analysis}

HUMAN FEEDBACK ON THE GAP ANALYSIS (if any): {gap_feedback or "none"}
HUMAN FEEDBACK ON A PREVIOUS BDD DRAFT (apply it if present): {bdd_feedback or "none"}

Write Gherkin .feature scenarios. Use these REAL credentials and data:
- Valid user: standard_user / secret_sauce
- Locked user: locked_out_user / secret_sauce
- Product: Sauce Labs Backpack at $29.99
- Checkout fields: First Name, Last Name, Zip/Postal Code
- Success message: "Thank you for your order!"
- Error format: "Epic sadface: <message>"

Produce these specific scenarios:

## FUNCTIONAL (@browser)
1. Successful login with standard_user → lands on /inventory.html
2. Locked user gets rejection error message
3. Add Sauce Labs Backpack to cart → cart badge shows "1"
4. Complete purchase: login → add to cart → checkout → fill info → finish → thank you page

## NONFUNCTIONAL (@api)
5. Accessing /inventory.html without login session shows error

Format as valid Gherkin with Feature, Scenario, Given/When/Then.
Output ONLY the Gherkin. No markdown fences. No explanation.
"""

    content = strip_fences(text_of(get_llm().invoke(prompt)))

    features_dir = PROJECT_ROOT / "features"
    features_dir.mkdir(exist_ok=True)
    (features_dir / "swag-labs.feature").write_text(content, encoding="utf-8")

    return {
        "bdd_scenarios": content,
        "current_node": "bdd_generator",
        "status": "waiting_human",
        "event_log": state.get("event_log", []) + [
            {"node": "bdd_generator", "event": "completed",
             "summary": "BDD scenarios ready — 4 browser + 1 API test"}
        ],
    }
