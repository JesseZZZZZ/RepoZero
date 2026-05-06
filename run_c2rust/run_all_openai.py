import json
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from datetime import datetime
from pathlib import Path
from run_terminal_agent_4_openai import run_reasoning_agent

REPO_ROOT = Path(__file__).resolve().parent.parent
model_name = "deepseek-v3.2"
actual_name = "deepseek-v3.2"
MAX_WORKERS = 10

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


def get_success_record_path(packages_root, repo_name):
    return os.path.join(packages_root, repo_name, "success_records.jsonl")


def is_already_succeeded(packages_root, repo_name, relative_path, lock):
    record_path = get_success_record_path(packages_root, repo_name)
    if not os.path.exists(record_path):
        return False
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line.strip())
                if entry.get("file_name") == relative_path:
                    return True
    except Exception:
        pass
    return False


def append_success_record(packages_root, repo_name, relative_path, package_dir, messages, lock):
    record_path = get_success_record_path(packages_root, repo_name)
    os.makedirs(os.path.dirname(record_path), exist_ok=True)

    trajectory_path = os.path.join(package_dir, "trajectory.jsonl")
    if messages:
        with open(trajectory_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    entry = json.dumps({
        "file_name": relative_path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trajectory": trajectory_path,
    }, ensure_ascii=False)
    with lock:
        with open(record_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")


def process_single_task(cpp_path, relative_path, repo_name, test_number, packages_root, lock):
    try:
        package_dir = os.path.join(packages_root, repo_name, f"test{test_number}_pkg")
        cargo_toml_path = os.path.join(package_dir, "Cargo.toml")
        rust_filename = f"test{test_number}.rs"
        output_rust_path = os.path.join(package_dir, rust_filename)

        if is_already_succeeded(packages_root, repo_name, relative_path, lock):
            with lock:
                print(f"[PID {os.getpid()}] Skipping (already succeeded): {relative_path}")
            return {"status": "skipped", "relative_path": relative_path}

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
"""
        with lock:
            print(f"[PID {os.getpid()}] Processing: {relative_path}")

        MAX_RETRIES = 1
        total_input_tokens = 0
        total_output_tokens = 0
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            token_info = run_reasoning_agent(prompt, model_name=model_name, cargo_toml_path=cargo_toml_path)

            if token_info and "error" not in token_info:
                total_input_tokens += token_info.get("input_tokens", 0)
                total_output_tokens += token_info.get("output_tokens", 0)

                if os.path.isfile(output_rust_path) and os.path.getsize(output_rust_path) > 0:
                    append_success_record(packages_root, repo_name, relative_path, package_dir, token_info.get("messages"), lock)
                    return {
                        "status": "success",
                        "relative_path": relative_path,
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                    }
                else:
                    last_error = f"Output file not generated: {output_rust_path} (attempt {attempt}/{MAX_RETRIES})"
                    with lock:
                        print(f"[PID {os.getpid()}] Warning {relative_path}: {last_error}")
            else:
                last_error = token_info.get("error", "API call failed") if token_info else "No response"
                with lock:
                    print(f"[PID {os.getpid()}] Warning {relative_path}: API error - {last_error} (attempt {attempt}/{MAX_RETRIES})")

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
Model: {actual_name}
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
    output_root = str(REPO_ROOT / "C2Rust" / "CppLarge" / "output_large" / actual_name)
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
                try:
                    result = future.result()
                except Exception as e:
                    task = future_to_task[future]
                    print(f"Worker process crashed: {task['relative_path']} - {e}")
                    failed_count += 1
                    continue
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
