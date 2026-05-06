import json
import os
import re
import subprocess
import shlex
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
model_name = "ernie-5.0"
MAX_WORKERS = 10

MINI_BIN = os.environ.get("MINI_SWE_AGENT_BIN", "mini")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

os.environ["MSWEA_COST_TRACKING"] = "ignore_errors"

gold_repos = [
    "Clipper",
    "sortedcontainers-cpp",
    "color",
    "indicators",
    "earcut.hpp",
    "immer",
    "hopscotch-map",
    "url-parser",
    "inflection-cpp",
    "idna-cpp",
]

cpp_to_rust_mapping = {
    "double-conversion-tests": "lexical-core / ryu (Rust fast float-to-string conversion crates)",
    "exprtk": "pest / chumsky / nom (Rust parser combinator crates)",
    "json11": "serde_json / json5 (Rust JSON serialization crates)",
    "lua": "mlua / rlua / lua-src (Rust Lua bindings and implementations)",
    "re2": "regex / fancy-regex (Rust regex crate)",
    "sqlpp11": "sqlparser-rust (Rust SQL parser crate)",
    "yaml-cpp": "serde_yaml / yaml-rust (Rust YAML serialization crates)",
}


def run_mini_swe_agent(task: str, working_dir: str = None):
    """Run mini-swe-agent and wait for completion."""
    inner_cmd = (
        f"ANTHROPIC_API_KEY={ANTHROPIC_API_KEY} "
        f"{MINI_BIN} "
        f"-m {shlex.quote(model_name)} "
        f"-y --exit-immediately "
        f"-t {shlex.quote(task)}"
    )
    if working_dir:
        inner_cmd = f"cd {shlex.quote(working_dir)} && " + inner_cmd

    try:
        process = subprocess.Popen(
            ["bash", "-c", inner_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        output_lines = []
        for line in process.stdout:
            print(line, end="", flush=True)
            output_lines.append(line)
        process.wait()
        return process.returncode == 0, "".join(output_lines)
    except Exception:
        return False, ""


def is_dir_empty(dir_path):
    """Return True if the directory does not exist or contains no non-empty files."""
    if not os.path.exists(dir_path):
        return True
    try:
        files = [f for f in os.listdir(dir_path) if not f.startswith(".")]
        for f in files:
            file_path = os.path.join(dir_path, f)
            if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                return False
        return True
    except Exception:
        return True


def process_single_task(cpp_path, relative_path, repo_name, test_number, packages_root, lock):
    try:
        package_dir = os.path.join(packages_root, repo_name, f"test{test_number}_pkg")
        rust_filename = f"test{test_number}.rs"
        output_rust_path = os.path.join(package_dir, rust_filename)

        if not is_dir_empty(package_dir):
            with lock:
                print(f"[PID {os.getpid()}] Skipping (directory exists): {relative_path}")
            return {"status": "skipped", "relative_path": relative_path}

        with lock:
            os.makedirs(package_dir, exist_ok=True)

        with open(cpp_path, "r", encoding="utf-8") as f:
            cpp_code = f.read()

        forbidden_crates = cpp_to_rust_mapping.get(repo_name, "none")

        prompt = f"""
You are an expert C++ to Rust migration engineer. Read the following C++ source code:

--- Source ({os.path.abspath(cpp_path)}) ---
{cpp_code}
---

Requirements:
1. **Environment**: Write pure Rust using the 2021 edition. Code must compile with `rustc` or as a Cargo project.

2. **CLI arguments**: The Rust binary must accept exactly the same command-line arguments as the C++ binary (same names, defaults, and required fields). Parse args via `std::env::args()`.

3. **Logic and output**: Algorithm logic, numeric precision, and string formatting must exactly match the C++ source. `println!` output must be byte-for-byte identical to `std::cout` output.

4. **Zero external dependencies**: Do NOT use any crates from crates.io (only `std`). Forbidden crates for this repo: {forbidden_crates}. Implement all functionality from scratch using the standard library.

5. **Project structure**: Create a complete Cargo project in `{os.path.abspath(package_dir)}`. Organize library code into modules. Place the entry test file `{rust_filename}` in the package root `{os.path.abspath(package_dir)}`.

6. **Black-box implementation**: Do not read the C++ library source. Infer behavior from the interface, then re-implement using `std`.

7. **Output**:
   - Create and implement library files inside `{os.path.abspath(package_dir)}`.
   - Save the entry file to `{os.path.abspath(output_rust_path)}`.
   - Compile and produce an executable at `{os.path.abspath(output_rust_path.replace(".rs", ""))}`.

Hint: `{os.path.abspath(cpp_path.replace(".cpp", ""))}` is the compiled C++ binary — use it to debug with any arguments.
You only have write access to `{os.path.abspath(package_dir)}`.
"""
        with lock:
            print(f"[PID {os.getpid()}] Processing: {relative_path}")

        MAX_RETRIES = 1
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            success, output = run_mini_swe_agent(prompt, working_dir=package_dir)

            if success and not is_dir_empty(package_dir):
                with lock:
                    print(f"[PID {os.getpid()}] Done: {relative_path}")
                return {
                    "status": "success",
                    "relative_path": relative_path,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            elif success:
                last_error = f"Output directory is empty (attempt {attempt}/{MAX_RETRIES})"
            else:
                last_error = f"mini-swe-agent failed (attempt {attempt}/{MAX_RETRIES})"

            with lock:
                print(f"[PID {os.getpid()}] Warning {relative_path}: {last_error}")

        return {"status": "failed", "relative_path": relative_path, "error": f"Failed after {MAX_RETRIES} retries: {last_error}"}

    except Exception as e:
        return {"status": "error", "relative_path": relative_path, "error": str(e)}


def collect_tasks_from_jsonl(jsonl_path, cpp_base_dir):
    tasks = []
    seen_files = set()

    if not os.path.exists(jsonl_path):
        print(f"Error: file not found: {jsonl_path}")
        return tasks

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line.strip())
            rel_path = data.get("file_name")

            if rel_path and rel_path not in seen_files:
                cpp_path = os.path.join(cpp_base_dir, rel_path)
                parts = rel_path.split("/")
                repo_name = parts[0]
                if repo_name not in gold_repos:
                    continue
                match = re.search(r"test(\d+)\.cpp", parts[-1])
                if match:
                    test_number = match.group(1)
                    tasks.append({
                        "cpp_path": cpp_path,
                        "relative_path": rel_path,
                        "repo_name": repo_name,
                        "test_number": test_number,
                    })
                    seen_files.add(rel_path)
    return tasks


def save_token_log(total_input_tokens, total_output_tokens, processed_count, failed_count, skipped_count, log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "token_usage.log")

    total_tokens = total_input_tokens + total_output_tokens
    avg_input  = total_input_tokens  / processed_count if processed_count > 0 else 0
    avg_output = total_output_tokens / processed_count if processed_count > 0 else 0
    avg_total  = total_tokens        / processed_count if processed_count > 0 else 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
{'='*60}
[{timestamp}] Token Usage
{'='*60}
Model: {model_name}
Success / Skipped / Failed: {processed_count} / {skipped_count} / {failed_count}
Total Input Tokens:  {total_input_tokens:,}
Total Output Tokens: {total_output_tokens:,}
Total Tokens:        {total_tokens:,}
Avg Input Tokens:    {avg_input:,.2f}
Avg Output Tokens:   {avg_output:,.2f}
Avg Total Tokens:    {avg_total:,.2f}
{'='*60}
"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"Token log saved to: {log_path}")
    return log_path


def main():
    cpp_base_dir = str(REPO_ROOT / "C2Rust" / "CppLarge")
    jsonl_path = os.path.join(cpp_base_dir, "test_cases_clean", "cleaned_test_cases.jsonl")
    output_root = str(REPO_ROOT / "C2Rust" / "CppLarge" / "output_mini_large" / model_name)
    packages_root = os.path.join(output_root, "packages")

    os.makedirs(packages_root, exist_ok=True)

    tasks = collect_tasks_from_jsonl(jsonl_path, cpp_base_dir)
    print(f"Found {len(tasks)} unique tasks in JSONL")
    print(f"Using {MAX_WORKERS} parallel workers")
    print("=" * 80)

    with Manager() as manager:
        lock = manager.Lock()
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_task = {
                executor.submit(
                    process_single_task,
                    task["cpp_path"],
                    task["relative_path"],
                    task["repo_name"],
                    task["test_number"],
                    packages_root,
                    lock,
                ): task for task in tasks
            }

            total_input_tokens = 0
            total_output_tokens = 0
            processed_count = 0
            failed_count = 0
            skipped_count = 0

            for future in as_completed(future_to_task):
                result = future.result()
                if result["status"] == "success":
                    total_input_tokens  += result.get("input_tokens", 0)
                    total_output_tokens += result.get("output_tokens", 0)
                    processed_count += 1
                elif result["status"] == "skipped":
                    skipped_count += 1
                else:
                    failed_count += 1
                    print(f"Task failed: {result['relative_path']} - {result.get('error')}")

    print("\n" + "=" * 60)
    print("Token Usage Summary")
    print("=" * 60)
    print(f"Success / Skipped / Failed: {processed_count} / {skipped_count} / {failed_count}")
    print(f"Total Tokens: {total_input_tokens + total_output_tokens:,}")
    print("=" * 60)

    save_token_log(
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        processed_count=processed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        log_dir=output_root,
    )


if __name__ == "__main__":
    main()
