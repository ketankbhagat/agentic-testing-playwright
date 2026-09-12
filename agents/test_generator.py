"""Node 4: Generate Playwright test code from BDD + exploration data."""
from agents.llm import PROJECT_ROOT, get_llm, strip_fences, text_of


def generate_tests(state: dict) -> dict:
    """Generate Playwright TypeScript tests for saucedemo.com."""
    bdd = state["bdd_scenarios"]
    exploration = state.get("app_exploration", "")
    bdd_feedback = state.get("bdd_feedback", "")
    test_feedback = state.get("test_feedback", "")
    requirement = state["requirement"]

    prompt = f"""You are a senior Playwright test engineer. Write TypeScript tests for https://www.saucedemo.com/.

REQUIREMENT: {requirement}

BDD SCENARIOS:
{bdd}

HUMAN FEEDBACK ON THE BDD (if any): {bdd_feedback or "none"}
HUMAN FEEDBACK ON A PREVIOUS TEST DRAFT (apply it if present): {test_feedback or "none"}

REAL PAGE STRUCTURE (from Playwright MCP exploration):
{exploration}

RULES:
1. `import {{ test, expect }} from '@playwright/test';`
2. baseURL is https://www.saucedemo.com — use `page.goto('/')` not the full URL
3. Use ONLY real selectors from the exploration data. Key ones:
   - Login: page.locator('#user-name'), page.locator('#password'), page.locator('#login-button')
   - Error: page.locator('[data-test="error"]')
   - Add to cart: page.locator('[data-test="add-to-cart-sauce-labs-backpack"]')
   - Cart badge: page.locator('.shopping_cart_badge')
   - Cart link: page.locator('.shopping_cart_link')
   - Checkout: page.locator('[data-test="checkout"]')
   - Checkout fields: page.locator('[data-test="firstName"]'), [data-test="lastName"], [data-test="postalCode"]
   - Continue: page.locator('[data-test="continue"]')
   - Finish: page.locator('[data-test="finish"]')
   - Complete: page.locator('.complete-header')
4. Credentials: standard_user / secret_sauce (valid), locked_out_user / secret_sauce (locked)
5. Write exactly 5 tests in this order:

test.describe('Swag Labs — Purchase Flow', () => {{

  test('1 — valid login redirects to inventory', ...)
    // Fill #user-name, #password, click #login-button
    // Expect URL: /inventory.html

  test('2 — locked user sees error message', ...)
    // Use locked_out_user / secret_sauce
    // Expect [data-test="error"] contains "locked out"

  test('3 — add Backpack to cart shows badge', ...)
    // Login first, then click add-to-cart-sauce-labs-backpack
    // Expect .shopping_cart_badge has text "1"

  test('4 — complete purchase end to end', ...)
    // Login → add backpack → cart → checkout → fill form → finish
    // Expect .complete-header has text "Thank you for your order!"

  test('5 — inventory page requires authentication', ...)
    // Navigate directly to /inventory.html WITHOUT logging in
    // Expect [data-test="error"] to be visible (auth error)

}});

6. Each test is independent — login fresh in each test, don't share state
7. Use await for all Playwright calls

Output ONLY the TypeScript code. No markdown fences. No explanation.
"""

    code = strip_fences(text_of(get_llm().invoke(prompt)))

    tests_dir = PROJECT_ROOT / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "swag-labs.spec.ts").write_text(code, encoding="utf-8")

    return {
        "test_code": code,
        "current_node": "test_generator",
        "status": "waiting_human",
        "event_log": state.get("event_log", []) + [
            {"node": "test_generator", "event": "completed",
             "summary": "5 Playwright tests generated — review before execution"}
        ],
    }
