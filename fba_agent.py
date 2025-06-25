"""Pipeline orchestrator for the Amazon FBA AI agent."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Tuple
import imaplib

try:
    from colorama import Fore, Style, init as colorama_init
except Exception:  # pragma: no cover - optional dependency
    class Fore:  # type: ignore
        RED = GREEN = YELLOW = ""

    class Style:  # type: ignore
        RESET_ALL = ""

    def colorama_init() -> None:  # type: ignore
        pass

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = lambda: None  # type: ignore


DATA_DIR = "data"
CONFIG_PATH = "config.json"
LOG_FILE = "log.txt"
OPENAI_MODEL = "gpt-4"

DEFAULT_BUDGET = 1500.0


OUTPUTS: Dict[str, str] = {
    "product_discovery": os.path.join(DATA_DIR, "product_results.csv"),
    "market_analysis": os.path.join(DATA_DIR, "market_analysis_results.csv"),
    "review_analysis": os.path.join(DATA_DIR, "review_analysis_results.csv"),
    "profitability_estimation": os.path.join(DATA_DIR, "profitability_estimation_results.csv"),
    "demand_forecast": os.path.join(DATA_DIR, "demand_forecast_results.csv"),
    "supplier_selection": os.path.join(DATA_DIR, "supplier_selection_results.csv"),
    "supplier_contact_generator": "supplier_messages",
    "pricing_simulator": os.path.join(DATA_DIR, "pricing_suggestions.csv"),
    "inventory_management": os.path.join(DATA_DIR, "inventory_management_results.csv"),
    "negotiation_agent": os.path.join("logs", "email_negotiation_log.txt"),
    "email_manager": "email_logs",
    "order_placement_agent": os.path.join("logs", "order_confirmation_log.txt"),
}

STEP_INPUTS = {
    "market_analysis": [OUTPUTS["product_discovery"]],
    "review_analysis": [OUTPUTS["market_analysis"]],
    "profitability_estimation": [OUTPUTS["market_analysis"]],
    "demand_forecast": [OUTPUTS["market_analysis"]],
    "supplier_selection": [OUTPUTS["profitability_estimation"], OUTPUTS["demand_forecast"]],
    "supplier_contact_generator": [OUTPUTS["supplier_selection"]],
    "pricing_simulator": [OUTPUTS["profitability_estimation"]],
    "inventory_management": [OUTPUTS["supplier_selection"]],
    "order_placement_agent": [OUTPUTS["supplier_selection"], OUTPUTS["supplier_contact_generator"]],
};


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Run the FBA pipeline")
    parser.add_argument("--auto", action="store_true", help="run without prompts")
    parser.add_argument("--resume", action="store_true", help="resume from last completed step")
    parser.add_argument("--from-step", help="start from given step")
    parser.add_argument("--reuse", action="store_true", help="reuse existing results when possible")
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="automatically fix validation errors and commit the changes",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="clear previous outputs and logs before running",
    )
    return parser.parse_args()


def log(msg: str) -> None:
    """Append a timestamped message to ``log.txt``."""

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def load_config() -> Dict[str, str]:
    """Return configuration from ``config.json`` if it exists."""

    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_openai_model(model: str) -> bool:
    """Return ``True`` if the given OpenAI model is accessible."""

    script = (
        "import os\n"
        "from openai import OpenAI\n"
        "client=OpenAI(api_key=os.getenv('OPENAI_API_KEY'))\n"
        "try:\n"
        "    ids=[m.id for m in client.models.list().data]\n"
        f"    print('1' if any(i.startswith('{model}') for i in ids) else '0')\n"
        "except Exception:\n"
        "    print('0')\n"
    )
    try:
        res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    except Exception:
        return False
    return res.stdout.strip() == "1"


def detect_services() -> Tuple[Dict[str, bool], str | None, str | None, str | None, bool]:
    """Detect API keys and model availability."""

    load_dotenv()
    config = load_config()

    serp = os.getenv("SERPAPI_API_KEY") or config.get("serpapi_key")
    keepa = os.getenv("KEEPA_API_KEY") or config.get("keepa_key")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = False
    if openai_key:
        openai_model = check_openai_model(OPENAI_MODEL)

    services = {
        "SerpAPI": bool(serp),
        "Keepa": bool(keepa),
        "OpenAI": bool(openai_key),
        OPENAI_MODEL: openai_model,
    }
    return services, serp, keepa, openai_key, openai_model


def request_missing_keys(serp: str | None, keepa: str | None, openai: str | None) -> Tuple[str | None, str | None, str | None]:
    """Prompt the user for any missing API keys."""

    if not serp:
        val = input("Enter your SerpAPI key (or leave blank): ").strip()
        serp = val or None
        if serp:
            os.environ["SERPAPI_API_KEY"] = serp
    if not keepa:
        val = input("Enter your Keepa API key (or leave blank): ").strip()
        keepa = val or None
        if keepa:
            os.environ["KEEPA_API_KEY"] = keepa
    if not openai:
        val = input("Enter your OpenAI API key (or leave blank): ").strip()
        openai = val or None
        if openai:
            os.environ["OPENAI_API_KEY"] = openai
    return serp, keepa, openai


def check_email_connection() -> bool:
    """Return ``True`` if email credentials are present."""

    if os.getenv("DISABLE_EMAIL", "").lower() in {"1", "true", "yes"}:
        return False
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    return bool(email_addr and password)


def print_service_status(services: Dict[str, bool]) -> None:
    """Display a summary of available services."""

    print("Service availability:")
    for name, ok in services.items():
        symbol = f"{Fore.GREEN}✓{Style.RESET_ALL}" if ok else f"{Fore.RED}✗{Style.RESET_ALL}"
        print(f"  {symbol} {name}")

    missing = [k for k, v in services.items() if not v]
    if missing:
        print("\nImplications:")
        if "SerpAPI" in missing:
            print(" - product_discovery will be skipped")
            print(" - market_analysis will use mock data")
        elif not services.get("SerpAPI") and not services.get("Keepa"):
            print(" - market_analysis will use mock data")
        if "OpenAI" in missing:
            print(" - supplier_contact_generator and pricing_simulator disabled")
        elif OPENAI_MODEL in missing:
            print(f" - {OPENAI_MODEL} unavailable; OpenAI modules will be skipped")
    else:
        print("All services available.")


def run_step(args: List[str], step: str, input_data: str | None = None, *, auto: bool = False) -> Tuple[str, float]:
    """Run a subprocess step and return ``(status, duration)``."""

    print(f"\n=== Running {step} ===")
    log(f"START {step}")
    start = time.time()
    try:
        subprocess.run([sys.executable] + args, check=True, text=True, input=input_data)
    except subprocess.CalledProcessError as exc:
        duration = time.time() - start
        print(f"{Fore.RED}✗ {step} failed: {exc}{Style.RESET_ALL}")
        log(f"RESULT {step} failed {duration:.1f}s {exc}")
        if auto:
            return "failed", duration
        while True:
            choice = input("Retry (r), skip (s) or abort (a)? [s]: ").strip().lower()
            if choice in {"r", "s", "a", ""}:
                break
        if choice == "r":
            return run_step(args, step, input_data, auto=auto)
        if choice == "a":
            log("ABORT")
            return "abort", duration
        log(f"RESULT {step} skipped {duration:.1f}s")
        return "skipped", duration
    else:
        duration = time.time() - start
        print(f"{Fore.GREEN}✓ {step} completed in {duration:.1f}s{Style.RESET_ALL}")
        log(f"RESULT {step} completed {duration:.1f}s")
        return "completed", duration


def _file_has_rows(path: str) -> bool:
    """Return ``True`` if CSV/dir has content beyond a header."""

    if os.path.isdir(path):
        try:
            return bool(os.listdir(path))
        except Exception:
            return False
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) > 1
    except Exception:
        return False


def check_output_exists(paths: List[str]) -> bool:
    """Return ``True`` if all files exist and contain data."""

    return all(_file_has_rows(p) for p in paths)


def ensure_mock_data(services: Dict[str, bool]) -> None:
    """Prepare mock data when no APIs are configured."""

    if not any(services.values()):
        run_step(["prepare_mock_data.py"], "prepare_mock_data")


def ask_reuse(step: str, paths: List[str], *, auto: bool = False, force: bool = False) -> bool:
    """Return ``True`` if existing outputs should be reused."""

    if not check_output_exists(paths):
        return False
    if force:
        print(f"{Fore.YELLOW}! Reusing cached results for {step}{Style.RESET_ALL}")
        log(f"RESULT {step} reused")
        return True
    if auto:
        return False
    choice = input(f"Existing results for {step} found. Reuse them? [y/N]: ").strip().lower()
    if choice == "y":
        print(f"{Fore.YELLOW}! Reusing cached results for {step}{Style.RESET_ALL}")
        log(f"RESULT {step} reused")
        return True
    return False


def _git_status() -> str:
    """Return ``git status --porcelain`` output or empty string on failure."""

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def run_validation(auto_fix: bool = False) -> bool:
    """Execute ``validate_all.py`` if available.

    Returns ``True`` if files were modified when ``auto_fix`` is ``True``.
    """
    if not os.path.exists("validate_all.py"):
        print("Validation script not found. Skipping validation step.")
        log("RESULT validation skipped missing")
        return False

    print("\n=== Validation Report ===")
    log("START validation")
    before = _git_status() if auto_fix else ""
    try:
        cmd = [sys.executable, "validate_all.py"] + (["--auto-fix"] if auto_fix else [])
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - execution failure
        print(f"Failed to run validation script: {exc}")
        log(f"RESULT validation failed launch {exc}")
        return False

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    proc.wait()
    status = "completed" if proc.returncode == 0 else f"failed {proc.returncode}"
    log(f"RESULT validation {status}")
    after = _git_status() if auto_fix else before
    return auto_fix and (before != after)


def load_last_statuses() -> Dict[str, str]:
    """Return step statuses from the last run recorded in ``log.txt``."""

    if not os.path.exists(LOG_FILE):
        return {}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = 0
    for i in range(len(lines) - 1, -1, -1):
        if "RUN START" in lines[i]:
            start = i
            break
    statuses: Dict[str, str] = {}
    for line in lines[start:]:
        if line.strip().startswith("RESULT"):
            parts = line.strip().split()
            if len(parts) >= 3:
                statuses[parts[1]] = parts[2]
    return statuses


def main() -> None:
    colorama_init()
    args = parse_args()
    if args.reset:
        try:
            import reset_pipeline
            reset_pipeline.reset()
        except Exception as exc:  # pragma: no cover - reset failure
            print(f"Reset failed: {exc}")

    log("RUN START")
    services, serp, keepa, openai_key, openai_model = detect_services()
    serp, keepa, openai_key = request_missing_keys(serp, keepa, openai_key)
    services = {
        "SerpAPI": bool(serp),
        "Keepa": bool(keepa),
        "OpenAI": bool(openai_key),
        OPENAI_MODEL: openai_model if openai_key else False,
    }
    negotiation_exists = os.path.exists("negotiation_agent.py")
    email_ok = check_email_connection()
    if not email_ok:
        print(
            f"{Fore.YELLOW}! Email modules disabled. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env to enable{Style.RESET_ALL}"
        )
    print_service_status(services)
    ensure_mock_data(services)

    if args.auto:
        budget = DEFAULT_BUDGET
    else:
        while True:
            try:
                budget = float(input("Enter your total startup budget in USD: "))
                break
            except ValueError:
                print("Please enter a valid number.")

    steps = [
        ("product_discovery", ["product_discovery.py"], f"{budget}\n", [OUTPUTS["product_discovery"]], services["SerpAPI"]),
        (
            "market_analysis",
            ["market_analysis.py", "--csv", OUTPUTS["product_discovery"] if services["SerpAPI"] else os.path.join(DATA_DIR, "mock_market_data.csv")],
            None,
            [OUTPUTS["market_analysis"]],
            services["SerpAPI"] or services["Keepa"],
        ),
        (
            "review_analysis",
            ["review_analysis.py", "--csv", OUTPUTS["market_analysis"]],
            None,
            [OUTPUTS["review_analysis"]],
            True,
        ),
        ("profitability_estimation", ["profitability_estimation.py"], None, [OUTPUTS["profitability_estimation"]], True),
        ("demand_forecast", ["demand_forecast.py"], None, [OUTPUTS["demand_forecast"]], True),
        (
            "supplier_selection",
            ["supplier_selection.py", "--budget", str(budget)],
            None,
            [OUTPUTS["supplier_selection"]],
            True,
        ),
        ("supplier_contact_generator", ["supplier_contact_generator.py"], None, [OUTPUTS["supplier_contact_generator"]], services["OpenAI"] and services[OPENAI_MODEL]),
        (
            "pricing_simulator",
            ["pricing_simulator.py"] + (["--auto"] if args.auto else []),
            None,
            [OUTPUTS["pricing_simulator"]],
            services["OpenAI"] and services[OPENAI_MODEL],
        ),
        ("inventory_management", ["inventory_management.py"], None, [OUTPUTS["inventory_management"]], True),
        (
            "negotiation_agent",
            ["negotiation_agent.py"],
            None,
            [OUTPUTS["negotiation_agent"]],
            negotiation_exists and services["OpenAI"] and services[OPENAI_MODEL] and email_ok,
        ),
        (
            "email_manager",
            ["email_manager.py"],
            None,
            [OUTPUTS["email_manager"]],
            email_ok,
        ),
        (
            "order_placement_agent",
            ["order_placement_agent.py"],
            None,
            [OUTPUTS["order_placement_agent"]],
            True,
        ),
    ]

    step_names = [s[0] for s in steps]
    statuses: Dict[str, str] = {name: "pending" for name in step_names}
    durations: Dict[str, float] = {name: 0.0 for name in step_names}
    generated: List[str] = []

    resume_states = load_last_statuses() if args.resume else {}

    start_index = 0
    if args.from_step and args.from_step in step_names:
        start_index = max(start_index, step_names.index(args.from_step))

    if args.resume and resume_states:
        last_done = -1
        for i, name in enumerate(step_names):
            if resume_states.get(name) == "completed":
                statuses[name] = "reused"
                last_done = i
        start_index = max(start_index, last_done + 1)

    pipeline_start = time.time()

    for idx, (name, cmd, inp, paths, condition) in enumerate(steps):
        if idx < start_index:
            continue
        if not condition:
            print(f"{Fore.YELLOW}! {name} skipped due to missing services{Style.RESET_ALL}")
            log(f"RESULT {name} skipped 0s service")
            statuses[name] = "skipped"
            continue
        reqs = STEP_INPUTS.get(name)
        if reqs and not all(_file_has_rows(p) for p in reqs):
            print(
                f"{Fore.YELLOW}! {name} skipped because required inputs are missing or empty{Style.RESET_ALL}"
            )
            log(f"RESULT {name} skipped 0s missing_input")
            statuses[name] = "skipped"
            continue
        if name == "review_analysis" and not os.path.exists(OUTPUTS["market_analysis"]):
            print(
                f"{Fore.YELLOW}! {name} skipped because market_analysis results are missing{Style.RESET_ALL}"
            )
            log(f"RESULT {name} skipped 0s missing_input")
            statuses[name] = "skipped"
            continue
        if name == "order_placement_agent":
            msgs_dir = OUTPUTS["supplier_contact_generator"]
            if not os.path.exists(OUTPUTS["supplier_selection"]) or not os.path.isdir(msgs_dir) or not os.listdir(msgs_dir):
                print(
                    f"{Fore.YELLOW}! {name} skipped due to missing supplier selection results or messages{Style.RESET_ALL}"
                )
                log(f"RESULT {name} skipped 0s missing_input")
                statuses[name] = "skipped"
                continue
        if ask_reuse(name, paths, auto=args.auto, force=args.reuse or statuses.get(name) == "reused"):
            statuses[name] = "reused"
            generated.extend(p for p in paths if os.path.exists(p))
            continue
        status, dur = run_step(cmd, name, inp, auto=args.auto)
        durations[name] = dur
        if status == "abort":
            print("Pipeline aborted.")
            log("RUN END")
            return
        statuses[name] = status
        if status in {"completed", "reused"}:
            for p in paths:
                if not os.path.exists(p):
                    print(f"{Fore.YELLOW}! Expected output {p} not found{Style.RESET_ALL}")
                    log(f"WARNING missing_output {p}")
                    continue
                generated.append(p)
                if not _file_has_rows(p):
                    print(f"{Fore.YELLOW}! {p} is empty{Style.RESET_ALL}")
                    log(f"WARNING empty_output {p}")

    total_time = time.time() - pipeline_start

    print("\n=== Summary ===")
    for step in step_names:
        state = statuses.get(step, "skipped")
        dur = durations.get(step, 0.0)
        if state == "completed":
            symbol = f"{Fore.GREEN}✓{Style.RESET_ALL}"
        elif state == "reused":
            symbol = f"{Fore.YELLOW}!{Style.RESET_ALL}"
        elif state == "failed":
            symbol = f"{Fore.RED}✗{Style.RESET_ALL}"
        else:
            symbol = f"{Fore.YELLOW}!{Style.RESET_ALL}"
        print(f" {symbol} {step}: {state} ({dur:.1f}s)")

    if generated:
        print("\nGenerated or reused files:")
        for path in generated:
            print(f" - {path}")

    print(f"\nTotal pipeline time: {total_time:.1f}s")

    warnings = [s for s, st in statuses.items() if st == "skipped"]
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f" - {w} was skipped")

    suggestions = []
    if not services.get("SerpAPI"):
        suggestions.append("SerpAPI")
    if not services.get("Keepa"):
        suggestions.append("Keepa")
    if not services.get("OpenAI"):
        suggestions.append("OpenAI")
    elif not services.get(OPENAI_MODEL):
        suggestions.append(f"access to {OPENAI_MODEL}")

    if suggestions:
        print("\nSubscriptions that would improve results: " + ", ".join(suggestions))

    modified = run_validation(auto_fix=args.auto_fix)

    if args.auto_fix and modified:
        try:
            branch = (
                subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
                )
                .strip()
            )
            log(f"GIT branch {branch}")
        except Exception as exc:  # pragma: no cover - git missing
            print(f"Warning: git not available ({exc})")
            log(f"GIT branch detection failed: {exc}")
        else:
            cmds = [
                ["git", "add", "."],
                ["git", "commit", "-m", "fix: auto-corrected validation errors"],
                ["git", "push", "origin", branch],
            ]
            for cmd in cmds:
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    log(f"GIT {' '.join(cmd)} -> {res.returncode}")
                    if res.stdout:
                        log(res.stdout.strip())
                    if res.stderr:
                        log(res.stderr.strip())
                    if res.returncode != 0:
                        print(
                            f"Warning: {' '.join(cmd)} failed ({res.stderr.strip()})"
                        )
                        break
                except Exception as exc:  # pragma: no cover - git failure
                    print(f"Warning: {' '.join(cmd)} failed ({exc})")
                    log(f"GIT {' '.join(cmd)} failed: {exc}")
                    break

    log("RUN END")


if __name__ == "__main__":
    main()

