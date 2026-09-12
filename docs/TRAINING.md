# Training Guide — Agentic Testing with LangGraph + Playwright

A self-paced course built around this repository. Each module explains a concept, points to the code
that implements it, and ends with a hands-on lab. Plan for **about 3 hours** in total.

| Module | Topic | Time |
|---|---|---|
| 0 | Setup and first run | 20 min |
| 1 | Why agentic testing? | 10 min |
| 2 | LangGraph fundamentals: state, nodes, edges | 25 min |
| 3 | Human-in-the-loop with checkpoints and interrupts | 25 min |
| 4 | RAG gap analysis | 20 min |
| 5 | Grounding tests in the real app | 20 min |
| 6 | Prompting for runnable code | 20 min |
| 7 | Execution, reporting and the self-healing loop | 20 min |
| 8 | Observability: the live dashboard | 15 min |
| 9 | Adapting it to your own application | 25 min |

**Before you start:** complete [Setup](../README.md#setup) in the README.

---

## Module 0 — Setup and first run

**Goal:** see the whole pipeline work once before studying any part of it.

### Lab 0.1 — Watch the simulation
1. `.\start.ps1` (Windows) or `./start.sh`.
2. In the dashboard, click **▶ Simulate demo**.
3. Click each node while it runs and read its output.

✅ **Check:** you can name the 6 agents and the 4 human gates in order.

### Lab 0.2 — Real run
1. In a second terminal, run `python main.py`.
2. Press Enter for the default requirement, and type `a` at every gate.
3. Watch Chromium open twice: exploration, then the tests.

✅ **Check:**
- `features/swag-labs.feature` and `tests/swag-labs.spec.ts` exist.
- The dashboard shows a green banner.
- http://localhost:8500/allure/ opens the report.

---

## Module 1 — Why agentic testing?

Traditional automation needs a person to read requirements, find gaps, write scenarios, locate
selectors, write code, run it and debug failures. Each step is well defined but slow.

An **agentic pipeline** hands each step to a specialised agent, and **keeps a human in charge of
the decisions**:

| Step | Manual | Here |
|---|---|---|
| Find what's untested | Read JIRA and docs | Gap Analyzer (RAG) |
| Write scenarios | BA/QA writes Gherkin | BDD Generator |
| Find selectors | DevTools inspection | App Explorer (live crawl) |
| Write test code | Engineer | Test Generator |
| Debug a failure | Engineer reads the trace | Fix Agent |
| **Decide what ships** | **Human** | **Human (4 gates)** |

**Key principle:** agents produce drafts and humans make decisions. An agent never silently writes
unreviewed code into your suite.

---

## Module 2 — LangGraph fundamentals

### Concepts

| Concept | Meaning | In this repo |
|---|---|---|
| **State** | One typed dict that every node reads and updates | `agents/state.py` → `QAState` |
| **Node** | A function `state → partial state update` | each file in `agents/` |
| **Edge** | A fixed transition between nodes | `graph.add_edge(...)` |
| **Conditional edge** | A function that picks the next node | `route_after_test` |
| **Compile** | Turns the graph into a runnable app | `graph.compile(...)` |

### Read the code
Open `agents/graph.py`. The whole workflow fits on one screen:

```python
graph.set_entry_point("analyze_gaps")
graph.add_edge("analyze_gaps", "generate_bdd")
graph.add_edge("generate_bdd", "explore_app")
graph.add_edge("explore_app", "generate_tests")
graph.add_edge("generate_tests", "run_tests")
graph.add_conditional_edges("run_tests", route_after_test,
                            {"suggest_fix": "suggest_fix", "done": END})
graph.add_edge("suggest_fix", "apply_fix")
graph.add_edge("apply_fix", "run_tests")      # ← the retry loop
```

A node returns **only the keys it changes**. For example, `agents/bdd_generator.py` returns:

```python
return {
    "bdd_scenarios": content,
    "current_node": "bdd_generator",
    "status": "waiting_human",
    "event_log": state.get("event_log", []) + [{...}],
}
```

### Lab 2.1 — Change the retry budget
In `main.py`, set `"max_retries": 1`. Now at most one fix is attempted. Explain which line in
`route_after_test` enforces this.

### Lab 2.2 — Draw the graph
Run:
```bash
python -c "from agents.graph import build_graph; print(build_graph().get_graph().draw_mermaid())"
```
Paste the output into https://mermaid.live and compare it with the README diagram.

✅ **Check:** you can explain why `apply_fix → run_tests` forms a loop that always ends.

---

## Module 3 — Human-in-the-loop

### How pausing works
1. `graph.compile(checkpointer=MemorySaver(), interrupt_before=[...])`
2. The **checkpointer** saves state after every step, per `thread_id`.
3. `interrupt_before=["generate_bdd", ...]` makes `app.stream(...)` **stop** before those nodes.
4. `app.get_state(config).next` tells you which node is waiting.
5. To continue, call `app.stream(None, config)`. Passing `None` means **resume from the
   checkpoint**. Passing the initial state again would restart the run.

### Approve vs. reject (in `main.py`)

```python
if approved:
    app.update_state(config, {gate["approved"]: True})
else:
    regen_node, regen_fn = gate["regen"]
    result = regen_fn({**snapshot.values, gate["feedback"]: feedback})
    app.update_state(config, result, as_node=regen_node)
```

`as_node=regen_node` records the new output **as if that node had just run again**. LangGraph
therefore works out the same next node, and the run pauses at the same gate for re-review.

| Gate | Paused before | Reviews | Rejection re-runs |
|---|---|---|---|
| 1 | `generate_bdd` | gap analysis | `analyze_gaps` |
| 2 | `explore_app` | BDD | `generate_bdd` |
| 3 | `run_tests` | test code | `generate_tests` |
| 4 | `apply_fix` | fix | `suggest_fix` |

### Lab 3.1 — Reject with feedback
Run `python main.py`. At gate 2, type `r` and enter:
`Add a scenario for checkout with an empty postal code`.
Confirm the regenerated BDD contains it, then approve.

### Lab 3.2 — Add a gate
Make exploration results reviewable: add `"generate_tests"` to `HUMAN_GATES` in `agents/graph.py`,
then add a matching entry in `GATES` in `main.py` (review key `app_exploration`, regen
`explore_app`). Run it and see the new pause.

✅ **Check:** you can explain why the second `app.stream` call passes `None`.

---

## Module 4 — RAG gap analysis

### Why RAG?
An LLM doesn't know your tickets. **Retrieval-Augmented Generation** puts the relevant ones into the
prompt, so the gap report cites *JIRA-204* instead of generic advice.

### Pipeline (`agents/gap_analyzer.py`)
1. **Load**: every `knowledge_base/*.md`.
2. **Chunk**: `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)`.
3. **Embed + index**: in-memory ChromaDB with the local all-MiniLM-L6-v2 model (no API key).
4. **Query**: the requirement text retrieves the top 8 chunks.
5. **Generate**: Claude writes Existing Coverage, Gaps, Fixes and Risk, citing JIRA ids.

A **fallback** keyword search runs if ChromaDB can't load, and the event summary shows which method
was used (`via chromadb` or `via keyword`).

### Lab 4.1 — Inspect retrieval
```bash
python -c "from agents.gap_analyzer import retrieve; d,m=retrieve('checkout tax total'); print(m); [print(x[:120],'\n---') for x in d]"
```

### Lab 4.2 — Add knowledge
Create `knowledge_base/JIRA-206-promo-codes.md` with acceptance criteria and a `**MISSING:**` line.
Re-run with the requirement `Add test coverage for promo codes at checkout`. The gap report should
cite JIRA-206.

✅ **Check:** you can say why chunk overlap exists.

---

## Module 5 — Grounding tests in the real app

### The hallucinated-selector problem
Asked to "test the login", an LLM happily writes `page.click('#loginBtn')`, which is plausible and
wrong. **Grounding** means showing it the real DOM first.

### How the explorer works (`agents/app_explorer.py`)
1. Python writes a Node script into the project folder, so `require('playwright')` resolves
   `node_modules`.
2. The script walks the flow: login → inventory → cart → checkout step 1 → step 2 → complete.
3. On each page it extracts inputs, buttons, `data-test` attributes, ids and text.
4. Claude condenses that raw JSON into a **Test Selector Reference** that is passed to the test
   generator.

This is a proof of concept for a **Playwright MCP server**, which gives an agent the same page
snapshots through the Model Context Protocol.

### Real gotcha found while building this
```js
await page.click('[data-test="finish"]');
await page.waitForURL('**/checkout-complete.html');
// The URL has changed, but React has NOT rendered the confirmation yet
await page.waitForSelector('.complete-header');   // ← required
```

### Lab 5.1 — Watch it
Set `HEADED=true` and run the pipeline to gate 2. Approve and watch the crawl. Then click
**App Explorer** in the dashboard to read the selector reference.

✅ **Check:** you can explain why `data-test` attributes are preferred over CSS classes.

---

## Module 6 — Prompting for runnable code

Open `agents/test_generator.py`. The prompt works because it is **specific**:

| Technique | Example from the prompt |
|---|---|
| Fix the imports | ``import { test, expect } from '@playwright/test';`` |
| Constrain navigation | "use `page.goto('/')` — baseURL is set" |
| Whitelist selectors | an explicit list of real locators |
| Fix the count and order | "Write exactly 5 tests in this order" |
| Require independence | "login fresh in each test, don't share state" |
| Control the output format | "Output ONLY the TypeScript code. No markdown fences." |

`strip_fences()` in `agents/llm.py` is a safety net for when the model adds fences anyway.

### Model settings (`agents/llm.py`)
- `QA_AGENT_MODEL` defaults to `claude-sonnet-5`.
- `max_tokens=8000`, so a full spec file isn't cut off.
- No `temperature`, because Claude 5 models reject it.

### Lab 6.1 — Break the prompt
Delete the selector whitelist from the prompt and run the pipeline. Compare the generated selectors
and the test results. Restore it afterwards.

✅ **Check:** you can list three prompt rules that directly prevent test failures.

---

## Module 7 — Execution, reporting and self-healing

### Test runner (`agents/test_runner.py`)
- `npx playwright test --reporter=allure-playwright,list`, run as a plain subprocess with no LLM.
- `test_passed = returncode == 0`.
- `npx allure generate allure-results -o allure-report` uses Allure 3, which needs no Java.

### Playwright config (`playwright.config.ts`)

```ts
use: {
  headless: !isHeaded,
  launchOptions: { slowMo: isHeaded ? 600 : 0 },   // must be inside launchOptions
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
},
workers: 1,
```

> ⚠️ `slowMo` placed directly under `use` is **silently ignored**. The run took 6 s instead of 22 s
> until it was moved.

### The fix loop (`agents/fix_agent.py`)
1. `suggest_fix` receives the failing code, the failure output and the selector reference, plus a
   list of **known site gotchas**.
2. It returns a complete corrected file, which you review at gate 4.
3. `apply_fix` writes it and increments `retry_count`. You then review at gate 3, and the tests
   re-run.

### A real failure the loop fixed
The generated test 5 assumed unauthenticated users are redirected:
```ts
await expect(page).toHaveURL('https://www.saucedemo.com/');   // ✘ URL stays /inventory.html
```
The fix agent replaced it with the behaviour the site actually has:
```ts
await expect(page.locator('[data-test="error"]')).toContainText("You can only access '/inventory.html'");
```

### Lab 7.1 — Inject a failure
In `tests/swag-labs.spec.ts`, change `toHaveText('1')` to `toHaveText('2')`. Then run:
```bash
npx playwright test
npx allure generate allure-results -o allure-report
```
Open the report, and find the screenshot and video for the failed test.

✅ **Check:** you can explain what stops the fix loop from running forever.

---

## Module 8 — Observability: the live dashboard

- `main.py` sends fire-and-forget `POST /api/event` calls, so a missing dashboard never breaks a
  run.
- `dashboard/server.py` stores events and fans them out to each browser over **Server-Sent
  Events**.
- `dashboard/static/index.html` maps each event to node and gate states: idle, running, done,
  failed, waiting, approved, rejected.

See the event table in the [README](../README.md#dashboard).

### Lab 8.1 — Watch the raw stream
With the dashboard running and a pipeline in progress:
```bash
curl -N http://localhost:8500/api/stream
```

### Lab 8.2 — Post your own event
```bash
curl -X POST http://localhost:8500/api/event -H "Content-Type: application/json" \
     -d '{"type":"waiting_human","node":"run_tests"}'
```
Watch the "review tests" gate turn amber.

✅ **Check:** you can explain why SSE fits this better than polling.

---

## Module 9 — Adapting it to your own application

A checklist for pointing the pipeline at another web app:

1. **Knowledge base:** replace `knowledge_base/*.md` with your tickets, specs and changelog. Mark
   known gaps with `**MISSING:**`.
2. **Base URL:** `playwright.config.ts` → `baseURL`.
3. **Explorer:** rewrite `EXPLORE_SCRIPT` in `agents/app_explorer.py` to walk your critical flow.
   Wait for elements, not just URLs.
4. **Prompts:** in `bdd_generator.py` and `test_generator.py`, replace the saucedemo credentials,
   products and selector whitelist.
5. **Gotchas:** list your app's quirks in the `fix_agent.py` prompt.
6. **Secrets:** use test accounts only, keep them in `.env`, and never in prompts that get logged.
7. **CI:** run with `HEADED=false python main.py --auto-approve`. Keep human gates for local and
   review workflows, since auto-approve removes the safety net.

### Capstone lab
Pick one additional flow on saucedemo.com, such as **product sorting (JIRA-205)**:
1. Enter a requirement for sorting coverage.
2. Reject the gap analysis once, with feedback on scope.
3. Extend the explorer to capture `.product_sort_container`.
4. Get all generated tests passing, using the fix loop if needed.
5. Share the Allure report.

---

## Glossary

| Term | Definition |
|---|---|
| **Agent** | An LLM-backed step with a narrow job and structured input and output |
| **BDD / Gherkin** | Behaviour-Driven Development scenarios written as Given / When / Then |
| **Checkpointer** | A LangGraph component that saves state so a run can pause and resume |
| **Grounding** | Giving the model real data (DOM, docs) so its output matches reality |
| **HITL** | Human-in-the-loop: a person approves or corrects agent output |
| **Interrupt** | A pause point in a compiled graph |
| **MCP** | Model Context Protocol, a standard way to expose tools such as a browser to agents |
| **RAG** | Retrieval-Augmented Generation: fetch relevant documents and add them to the prompt |
| **SSE** | Server-Sent Events, a one-way live stream from server to browser |
| **slowMo** | Playwright delay between actions, used so humans can follow along |
