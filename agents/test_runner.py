"""Node 5: Execute Playwright tests and generate Allure report."""
import os
import re
import shutil
import subprocess

from agents.llm import PROJECT_ROOT

# npx is npx.cmd on Windows; resolve it so subprocess can launch it without a shell
NPX = shutil.which("npx") or "npx"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def run_tests(state: dict) -> dict:
    """Run Playwright tests in a VISIBLE browser and generate Allure report."""
    results_dir = PROJECT_ROOT / "allure-results"
    if results_dir.exists():
        shutil.rmtree(results_dir)

    env = os.environ.copy()
    if env.get("HEADED", "true").lower() != "false":
        print("\n🖥️  Opening browser — watch the tests execute...\n")
    else:
        print("\n⚡ Running headless (set HEADED=true for visible browser)\n")

    # Tests run in VISIBLE browser with slowMo — give plenty of time
    try:
        result = subprocess.run(
            [NPX, "playwright", "test", "--reporter=allure-playwright,list"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300, cwd=PROJECT_ROOT, env=env,
        )
        stdout = ANSI.sub("", result.stdout + "\n" + result.stderr)
        passed = result.returncode == 0
    except subprocess.TimeoutExpired as e:
        stdout = f"Playwright run timed out after 300s\n{e.stdout or ''}"
        passed = False
    print(stdout[-3000:])

    report_path = PROJECT_ROOT / "allure-report"
    report_ok = False
    try:
        gen = subprocess.run(
            [NPX, "allure", "generate", "allure-results", "-o", "allure-report"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=PROJECT_ROOT,
        )
        report_ok = gen.returncode == 0 and (report_path / "index.html").exists()
        if not report_ok:
            print(f"⚠️  Allure report not generated (needs Java on PATH): {gen.stderr.strip()[:300]}")
    except Exception as e:
        print(f"⚠️  Allure report not generated: {e}")

    return {
        "test_stdout": stdout[-5000:],
        "test_passed": passed,
        "allure_report_path": str(report_path) if report_ok else "",
        "current_node": "test_runner",
        "status": "passed" if passed else "waiting_human",
        "event_log": state.get("event_log", []) + [
            {"node": "test_runner", "event": "completed",
             "summary": f"Tests {'PASSED' if passed else 'FAILED'}"
                        + (" — see allure-report/" if report_ok else "")}
        ],
    }
