"""Node 3: Explore saucedemo.com using Playwright to gather real page structure.

POC stand-in for the Playwright MCP server. In production, this would connect to
a Playwright MCP server via the MCP protocol. For this demo, we run Playwright
directly to navigate pages, extract DOM structure, and feed real selectors into
test generation.
"""
import json
import os
import subprocess

from agents.llm import PROJECT_ROOT, get_llm, text_of

# Explore the full purchase flow — login, inventory, cart, checkout, complete
EXPLORE_SCRIPT = '''
const { chromium } = require('playwright');

(async () => {
    // VISIBLE browser — audience watches MCP exploration crawl through the app
    const isHeaded = process.env.HEADED !== 'false';
    const browser = await chromium.launch({
        headless: !isHeaded,
        slowMo: isHeaded ? 400 : 0,
    });
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await context.newPage();

    const results = {};

    // --- Page 1: Login page ---
    await page.goto('https://www.saucedemo.com/', { waitUntil: 'domcontentloaded', timeout: 15000 });
    results.login = await page.evaluate(() => {
        const els = [];
        document.querySelectorAll('input, button, [data-test], .error-message-container, a').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                id: el.id || null,
                dataTest: el.getAttribute('data-test'),
                text: (el.textContent || '').trim().substring(0, 80),
                placeholder: el.placeholder || null,
                className: el.className || null,
            });
        });
        return { url: window.location.href, title: document.title, elements: els };
    });

    // --- Login and go to inventory ---
    await page.fill('#user-name', 'standard_user');
    await page.fill('#password', 'secret_sauce');
    await page.click('#login-button');
    await page.waitForURL('**/inventory.html', { timeout: 10000 });

    // --- Page 2: Inventory page ---
    results.inventory = await page.evaluate(() => {
        const els = [];
        document.querySelectorAll('button, [data-test], .inventory_item, select, a, .shopping_cart_link, .shopping_cart_badge').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                id: el.id || null,
                dataTest: el.getAttribute('data-test'),
                text: (el.textContent || '').trim().substring(0, 80),
                className: el.className || null,
            });
        });
        const products = [...document.querySelectorAll('.inventory_item')].map(item => ({
            name: item.querySelector('.inventory_item_name')?.textContent?.trim(),
            price: item.querySelector('.inventory_item_price')?.textContent?.trim(),
            addButton: item.querySelector('button')?.getAttribute('data-test'),
        }));
        return { url: window.location.href, title: document.title, elements: els, products };
    });

    // --- Add Backpack to cart, go to cart ---
    await page.click('[data-test="add-to-cart-sauce-labs-backpack"]');
    const badgeText = await page.textContent('.shopping_cart_badge').catch(() => 'none');
    results.cartBadge = badgeText;

    await page.click('.shopping_cart_link');
    await page.waitForURL('**/cart.html', { timeout: 5000 });

    // --- Page 3: Cart page ---
    results.cart = await page.evaluate(() => {
        const els = [];
        document.querySelectorAll('button, [data-test], .cart_item, a').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                dataTest: el.getAttribute('data-test'),
                text: (el.textContent || '').trim().substring(0, 80),
                id: el.id || null,
            });
        });
        return { url: window.location.href, elements: els };
    });

    // --- Checkout step one ---
    await page.click('[data-test="checkout"]');
    await page.waitForURL('**/checkout-step-one.html', { timeout: 5000 });

    results.checkoutOne = await page.evaluate(() => {
        const els = [];
        document.querySelectorAll('input, button, [data-test]').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                dataTest: el.getAttribute('data-test'),
                placeholder: el.placeholder || null,
                id: el.id || null,
            });
        });
        return { url: window.location.href, elements: els };
    });

    // --- Fill checkout, go to step two ---
    await page.fill('[data-test="firstName"]', 'Test');
    await page.fill('[data-test="lastName"]', 'User');
    await page.fill('[data-test="postalCode"]', '30301');
    await page.click('[data-test="continue"]');
    await page.waitForURL('**/checkout-step-two.html', { timeout: 5000 });

    results.checkoutTwo = await page.evaluate(() => {
        const els = [];
        document.querySelectorAll('button, [data-test], .summary_total_label, .summary_info_label, .summary_value_label').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                dataTest: el.getAttribute('data-test'),
                text: (el.textContent || '').trim().substring(0, 80),
                className: el.className || null,
            });
        });
        return { url: window.location.href, elements: els };
    });

    // --- Finish order ---
    await page.click('[data-test="finish"]');
    await page.waitForURL('**/checkout-complete.html', { timeout: 5000 });
    // The SPA updates the URL before it re-renders — wait for the confirmation itself
    await page.waitForSelector('.complete-header', { timeout: 5000 }).catch(() => {});

    results.complete = await page.evaluate(() => {
        const header = document.querySelector('.complete-header')?.textContent?.trim();
        const els = [];
        document.querySelectorAll('button, [data-test], .complete-header, .complete-text').forEach(el => {
            els.push({
                tag: el.tagName.toLowerCase(),
                dataTest: el.getAttribute('data-test'),
                text: (el.textContent || '').trim().substring(0, 80),
                className: el.className || null,
            });
        });
        return { url: window.location.href, completeHeader: header, elements: els };
    });

    console.log(JSON.stringify(results, null, 2));
    await browser.close();
})().catch(err => { console.error(err); process.exit(1); });
'''


def _compact(raw: str) -> str:
    """Drop null fields so more real selectors fit in the LLM prompt."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if v not in (None, "")}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value

    return json.dumps(clean(data), separators=(",", ":"))


def explore_app(state: dict) -> dict:
    """
    Navigate saucedemo.com through the full purchase flow using Playwright.
    Extracts real DOM structure from every page: login, inventory, cart, checkout, complete.
    This is the Playwright MCP POC — same data a MCP snapshot would produce.
    """
    # The script must live inside the project so require('playwright') resolves node_modules
    script_path = PROJECT_ROOT / ".explore-app.tmp.js"
    script_path.write_text(EXPLORE_SCRIPT, encoding="utf-8")

    env = os.environ.copy()
    if env.get("HEADED", "true").lower() != "false":
        print("\n🌐 Opening browser — watching MCP exploration crawl through saucedemo.com...\n")

    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=PROJECT_ROOT, env=env,
        )
        exploration_data = result.stdout.strip()
        if result.returncode != 0 or not exploration_data:
            exploration_data = json.dumps({
                "error": (result.stderr or "No output")[:1500],
                "partial_stdout": exploration_data[:1500],
                "fallback": True,
            })
    except Exception as e:
        exploration_data = json.dumps({"error": str(e), "fallback": True})
    finally:
        script_path.unlink(missing_ok=True)

    summary_prompt = f"""You explored https://www.saucedemo.com/ through the full purchase flow using
Playwright browser automation (MCP-style page snapshots). Here is the raw DOM extraction:

{_compact(exploration_data)[:12000]}

Produce a **Test Selector Reference** — organized by page — that a Playwright test author
can copy-paste from. For each page list:

1. **URL pattern** (e.g. **/inventory.html)
2. **Key elements** with their best Playwright locator:
   - Prefer: page.locator('[data-test="..."]') or page.locator('#id')
   - Fallback: page.getByRole(...) or page.getByText(...)
3. **User actions possible** on that page
4. **Assertions to make** (what to expect after each action)

Cover: Login, Inventory, Cart, Checkout Step 1, Checkout Step 2, Checkout Complete.
If the extraction reports an error, say so at the top and fall back to these known selectors:
#user-name, #password, #login-button, [data-test="error"],
[data-test="add-to-cart-sauce-labs-backpack"], .shopping_cart_link, .shopping_cart_badge,
[data-test="checkout"], [data-test="firstName"], [data-test="lastName"], [data-test="postalCode"],
[data-test="continue"], [data-test="finish"], .complete-header.
"""

    summary = text_of(get_llm().invoke(summary_prompt))
    failed = '"fallback": true' in exploration_data

    return {
        "app_exploration": summary,
        "current_node": "app_explorer",
        "event_log": state.get("event_log", []) + [
            {"node": "app_explorer", "event": "completed",
             "summary": "Exploration FAILED — used known selectors" if failed
             else "Explored 6 pages via Playwright — login through checkout complete"}
        ],
    }
