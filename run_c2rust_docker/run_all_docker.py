import json
import os
import re
import subprocess
import sys
import time
import posixpath
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from multiprocessing import Manager

# Add current directory to path to import run_terminal_agent
sys.path.insert(0, os.path.dirname(__file__))
from run_terminal_agent import run_reasoning_agent

# Host path configuration
REPO_ROOT = Path(__file__).resolve().parent.parent
HOST_DATASET_ROOT = str(REPO_ROOT / "C2Rust" / "CppLarge")

# Docker internal path configuration
CONTAINER_WORKSPACE = "/workspace"
CONTAINER_DATASET_ROOT = f"{CONTAINER_WORKSPACE}/dataset"

# Docker image configuration
DOCKER_IMAGE = os.getenv("REPOZERO_DOCKER_IMAGE", "ghcr.io/jessezzzzz/c2rust-arena:latest")

# Model configuration
model_name = os.getenv("MODEL_NAME", "deepseek-v3.1-250821")
actual_name = os.getenv("MODEL_NAME", "deepseek-v3.1-250821")
import argparse

parser = argparse.ArgumentParser(description="Run Docker-based evaluation with concurrent processes")
parser.add_argument(
    "-k", "--num-processes",
    type=int,
    default=4,
    help="Number of concurrent processes (default: 4)"
)
parser.add_argument(
    "-m", "--model",
    type=str,
    default=None,
    help="Model name to use (overrides MODEL_NAME env var)"
)
args = parser.parse_args()

if args.model:
    model_name = args.model
    actual_name = args.model
# Gold repos list
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

# C++ to Rust mapping (forbidden crates)
cpp_to_rust_mapping = {
    "double-conversion-tests": "lexical-core / ryu (Rust fast float-to-string conversion crates)",
    "exprtk": "pest / chumsky / nom (Rust parser combinator crates)",
    "json11": "serde_json / json5 (Rust JSON serialization crates)",
    "lua": "mlua / rlua / lua-src (Rust Lua bindings and implementations)",
    "re2": "regex / fancy-regex (Rust regex crate)",
    "sqlpp11": "sqlparser-rust (Rust SQL parser crate)",
    "yaml-cpp": "serde_yaml / yaml-rust (Rust YAML serialization crates)",
}


def run_docker_command(cmd, timeout=60):
    """Execute Docker command"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timeout: {cmd}"
    except Exception as e:
        return False, "", str(e)


def run_docker_cp(src_path, container_name, dst_path, timeout=60):
    """Execute docker cp command (use list args to avoid shell parsing issues)"""
    try:
        result = subprocess.run(
            ["docker", "cp", src_path, f"{container_name}:{dst_path}"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timeout"
    except Exception as e:
        return False, "", str(e)


def ensure_image_exists(image_name):
    """
    Ensure Docker image exists, pull from registry if not

    Args:
        image_name: Docker image name (including registry)

    Returns:
        True on success, False on failure
    """
    # Check if local image exists
    success, stdout, stderr = run_docker_command(
        f"docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}}' | grep '^{image_name}$'",
        timeout=10
    )
    if success and image_name in stdout:
        print(f"[OK] Docker image {image_name} already exists locally")
        return True

    # Pull image from registry
    print(f"[PULL] Image {image_name} not found locally, pulling from registry...")
    success, stdout, stderr = run_docker_command(f"docker pull {image_name}", timeout=300)
    if success:
        print(f"[OK] Docker image {image_name} pulled successfully")
        return True
    else:
        print(f"[ERROR] Failed to pull Docker image {image_name}: {stderr}")
        return False


def create_task_container(task_name, cpp_path=None):
    """
    Create temporary Docker container for single task

    Args:
        task_name: Task name (e.g., Clipper/test1.cpp -> Clipper-test1)
        cpp_path: C++ file host path for copying into container

    Returns:
        New container name, or None on failure
    """
    new_container_name = f"repoarena-{task_name.replace('/', '-').replace('.cpp', '')}"

    # Step 1: Ensure image exists
    if not ensure_image_exists(DOCKER_IMAGE):
        return None

    # Step 2: Check if container exists, delete if so
    exists, stdout, stderr = run_docker_command(
        f"docker ps -a --filter name={new_container_name} --format '{{{{.Names}}}}'"
    )
    if exists and new_container_name in stdout:
        print(f"[CLEANUP] Container {new_container_name} already exists, removing...")
        run_docker_command(f"docker rm -f {new_container_name}")

    # Step 3: Start container from image
    docker_cmd = f"docker run -d --name {new_container_name} "
    docker_cmd += f"--network none "                                   # No network
    docker_cmd += f"-w {CONTAINER_WORKSPACE} "                      # Set working directory
    docker_cmd += f"{DOCKER_IMAGE} tail -f /dev/null"

    success, stdout, stderr = run_docker_command(docker_cmd, timeout=30)

    if not success:
        print(f"[ERROR] Failed to start container: {stderr}")
        return None

    # Verify container status: network isolation check
    success, stdout, stderr = run_docker_command(
        f"docker exec {new_container_name} cat /sys/class/net/lo/iflink",
        timeout=10
    )
    if success and stdout.strip() == "1":
        print(f"[OK] Container {new_container_name} network isolation normal (lo only)")

    # Copy C++ file and pre-compiled executable into container
    if cpp_path:
        cpp_filename = os.path.basename(cpp_path)
        module_name = cpp_filename.replace(".cpp", "")

        # Find pre-compiled executable file
        # Try multiple patterns:
        # 1. repo_root/testN_executable (e.g., immer)
        # 2. repo_root/testN (e.g., immer)
        # 3. repo_root/tests/testN (e.g., Clipper)
        # 4. repo_root/tests/testN_executable
        host_cpp_dir = os.path.dirname(cpp_path)  # Could be repo_root or repo_root/tests
        exe_parent_dir = os.path.dirname(host_cpp_dir)  # Go up one more level if needed

        # Try different patterns
        exe_candidates = [
            os.path.join(host_cpp_dir, f"{module_name}_executable"),
            os.path.join(host_cpp_dir, module_name),
            os.path.join(exe_parent_dir, "tests", f"{module_name}_executable"),
            os.path.join(exe_parent_dir, "tests", module_name),
        ]

        host_executable_path = None
        exe_filename = None

        for candidate_path in exe_candidates:
            if os.path.exists(candidate_path):
                host_executable_path = candidate_path
                exe_filename = os.path.basename(candidate_path)
                break

        if not host_executable_path:
            print(f"[WARNING] Pre-compiled file not found for {module_name} in: {host_cpp_dir} or {exe_parent_dir}/tests")
            return None

        # Container internal paths
        container_dataset_dir = CONTAINER_DATASET_ROOT
        container_executable_path = posixpath.join(container_dataset_dir, exe_filename)
        container_cpp_path = posixpath.join(container_dataset_dir, cpp_filename)

        # Ensure container directory exists
        run_docker_command(
            f"docker exec {new_container_name} mkdir -p {container_dataset_dir} 2>&1",
            timeout=10
        )

        # Copy executable file
        success, _, _ = run_docker_cp(host_executable_path, new_container_name, container_executable_path, timeout=10)
        if success:
            print(f"[OK] Container {new_container_name} executable copied to {container_executable_path}")
            # Set executable permission
            run_docker_command(
                f"docker exec {new_container_name} chmod +x {container_executable_path} 2>&1",
                timeout=10
            )
            # Ensure executable has _executable suffix for consistent naming
            if not exe_filename.endswith("_executable"):
                # Rename to have _executable suffix
                target_name = f"{module_name}_executable"
                target_path = posixpath.join(container_dataset_dir, target_name)
                run_docker_command(
                    f"docker exec {new_container_name} mv {container_executable_path} {target_path} 2>&1",
                    timeout=10
                )
                exe_filename = target_name
                container_executable_path = target_path
                print(f"[OK] Renamed executable to {target_name}")
        else:
            print(f"[WARNING] Container {new_container_name} failed to copy executable file")
            return None

        # Copy source file (agent can view)
        run_docker_cp(cpp_path, new_container_name, container_cpp_path, timeout=10)
        print(f"[OK] Container {new_container_name} source code copied to {container_cpp_path}")

    print(f"[OK] Created container: {new_container_name}")
    return new_container_name


def cleanup_task_container(container_name):
    """Cleanup task container"""
    run_docker_command(f"docker rm -f {container_name}")


def get_success_record_path(packages_root, repo_name):
    return os.path.join(packages_root, repo_name, "success_records.jsonl")


def is_already_succeeded(packages_root, repo_name, relative_path):
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


def append_success_record(packages_root, repo_name, relative_path, package_dir, messages):
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
    with open(record_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def append_trajectory_log(log_dir, actual_name, relative_path, messages, result):
    """Append trajectory entry to global log file"""
    if not messages:
        return

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{actual_name}.jsonl")

    entry = {
        "file_name": relative_path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "result": result,
        "messages": messages,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def process_single_task(cpp_path, relative_path, repo_name, test_number, packages_root, host_output_root, actual_name):
    """
    Process single task

    Args:
        cpp_path: Host absolute path of C++ file
        relative_path: Relative path to dataset (e.g., Clipper/test1.cpp)
        repo_name: Repository name
        test_number: Test number
        packages_root: Host packages root directory
        host_output_root: Host output root directory
        actual_name: Model/run name for logging

    Returns:
        Processing result dictionary
    """
    try:
        package_dir = os.path.join(packages_root, repo_name, f"test{test_number}_pkg")
        output_dir = "/output"
        rust_filename = f"test{test_number}.rs"
        output_rust_path = os.path.join(package_dir, rust_filename)

        if is_already_succeeded(packages_root, repo_name, relative_path):
            print(f"[SKIP] {relative_path} already succeeded")
            return {
                "status": "skipped",
                "relative_path": relative_path,
            }

        os.makedirs(package_dir, exist_ok=True)

        # Read C++ code
        with open(cpp_path, "r", encoding="utf-8") as f:
            cpp_code = f.read()

        # Container internal executable path
        cpp_filename = os.path.basename(cpp_path)
        module_name = cpp_filename.replace(".cpp", "")
        exe_filename = f"{module_name}_executable"
        container_executable_path = posixpath.join(CONTAINER_DATASET_ROOT, exe_filename)

        forbidden_crates = cpp_to_rust_mapping.get(repo_name, "none")

        # Build prompt for Agent
        prompt = f"""
You are an expert C++ to Rust migration engineer. Read the following C++ source code:

--- Source ({os.path.join(CONTAINER_DATASET_ROOT, relative_path)}) ---
{cpp_code}
---

Requirements:
1. **Environment**: Write pure Rust using the 2021 edition. Code must compile with `rustc` or as a Cargo project.

2. **CLI arguments**: The Rust binary must accept exactly the same command-line arguments as the C++ binary (same names, defaults, and required fields). Parse args via `std::env::args()`.

3. **Logic and output**: Algorithm logic, numeric precision, and string formatting must exactly match the C++ source. `println!` output must be byte-for-byte identical to `std::cout` output.

4. **Zero external dependencies**: Do NOT use any crates from crates.io (only `std`). Forbidden crates for this repo: {forbidden_crates}. Implement all functionality from scratch using the standard library.

5. **Project structure**: Create a complete Cargo project in `{output_dir}`. Organize library code into modules. Place the entry test file `{rust_filename}` in the package root `{output_dir}`.

6. **Black-box implementation**: Do not read the C++ library source. Infer behavior from the interface, then re-implement using `std`.

7. **Output**:
   - Create and implement library files inside `{output_dir}`.
   - Save the entry file to `{output_dir}/{rust_filename}`.
   - Compile and produce an executable at `{output_dir}/{rust_filename}` (by running `rustc {rust_filename}` or `cargo build --release`).

Hint: `{container_executable_path}` is the compiled C++ binary — use it to debug with any arguments.
"""

        # Create task container
        task_name = relative_path.replace('.cpp', '')
        task_container = create_task_container(task_name, cpp_path=cpp_path)
        if not task_container:
            return {
                "success": False,
                "relative_path": relative_path,
                "error": "Failed to create task container"
            }

        try:
            print(f"[OK] Container {task_container} ready")

            print(f"\n{'='*60}")
            print(f"Processing: {relative_path}")
            print(f"Container: {task_container}")
            print(f"{'='*60}\n")

            # Call Agent to execute task inside Docker container
            token_info = run_reasoning_agent(prompt, container_name=task_container, model_name=model_name)

            # Get token statistics
            input_tokens = token_info.get("input_tokens", 0) if token_info else 0
            output_tokens = token_info.get("output_tokens", 0) if token_info else 0
            messages = token_info.get("messages") if token_info else None
            agent_success = True

            print(f"\n[Completed] {relative_path} | Input={input_tokens}, Output={output_tokens}")

        except Exception as agent_error:
            # Agent failed, but still try to copy output
            print(f"\n[ERROR] Agent execution failed: {agent_error}")
            input_tokens = 0
            output_tokens = 0
            messages = None
            agent_success = False

        try:
            # Always try to copy output files from container to host
            print(f"[COPY] Copying output files to host: {package_dir}")
            copy_success, stdout, stderr = run_docker_command(
                f"docker cp {task_container}:{output_dir}/. {package_dir}",
                timeout=30
            )
            if copy_success:
                print(f"[OK] Output files synced to: {package_dir}")
                # List copied files
                files = os.listdir(package_dir) if os.path.exists(package_dir) else []
                if files:
                    print(f"   Generated files: {files}")
            else:
                print(f"[WARNING] Failed to copy output: {stderr}")

            # Check if output file exists and has content
            if os.path.isfile(output_rust_path) and os.path.getsize(output_rust_path) > 0:
                append_success_record(
                    packages_root,
                    repo_name,
                    relative_path,
                    package_dir,
                    messages
                )
                log_dir = os.path.join(REPO_ROOT, "logs", "C2Rust")
                append_trajectory_log(log_dir, actual_name, relative_path, messages, "success")
                return {
                    "success": True,
                    "relative_path": relative_path,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "container": task_container,
                    "output_dir": package_dir,
                    "status": "success",
                }
            else:
                print(f"[WARNING] Output file not generated: {output_rust_path}")
                log_dir = os.path.join(REPO_ROOT, "logs", "C2Rust")
                append_trajectory_log(log_dir, actual_name, relative_path, messages, "failed")
                return {
                    "success": False,
                    "relative_path": relative_path,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "error": "Output file not generated" if agent_success else f"Agent failed: {agent_error}"
                }

        finally:
            # Cleanup container
            print(f"[CLEANUP] Cleaning container: {task_container}")
            cleanup_task_container(task_container)

    except Exception as e:
        print(f"\n[ERROR] {relative_path} | {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "relative_path": relative_path,
            "error": str(e)
        }


def collect_tasks_from_jsonl(jsonl_path, cpp_base_dir):
    """Collect tasks from JSONL file"""
    tasks = []
    seen_files = set()

    if not os.path.exists(jsonl_path):
        print(f"[ERROR] File not found: {jsonl_path}")
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

                # Only process gold repos
                if repo_name not in gold_repos:
                    continue

                # Match testN.cpp pattern
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
    """Save token usage log"""
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


def save_progress(progress_file, total, results):
    """Save progress to file"""
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "processed": len(results),
            "results": results
        }, f, indent=2)


def main(num_processes=4):
    global model_name
    global actual_name

    # Output configuration - RepoZero/output/C2Rust/{actual_name}
    host_output_root = str(REPO_ROOT / "output" / "C2Rust" / actual_name)
    packages_root = os.path.join(host_output_root, "packages")

    # Ensure directories exist
    os.makedirs(packages_root, exist_ok=True)

    # JSONL file path
    jsonl_path = os.path.join(REPO_ROOT, "C2Rust", "cleaned_test_cases.jsonl")

    # Collect tasks from JSONL
    tasks = collect_tasks_from_jsonl(jsonl_path, HOST_DATASET_ROOT)
    print(f"Found {len(tasks)} tasks in JSONL")
    print(f"Gold repos: {gold_repos}")

    if not tasks:
        print("No tasks to process")
        return

    print(f"Found {len(tasks)} tasks to process\n")

    # Show first task's prompt for confirmation
    sample_task = tasks[0]
    sample_cpp_path = sample_task["cpp_path"]
    sample_relative_path = sample_task["relative_path"]
    sample_repo_name = sample_task["repo_name"]
    sample_test_number = sample_task["test_number"]

    with open(sample_cpp_path, "r", encoding="utf-8") as f:
        sample_cpp_code = f.read()

    sample_module_name = os.path.basename(sample_cpp_path).replace('.cpp', '')
    sample_executable_path = posixpath.join(CONTAINER_DATASET_ROOT, f"{sample_module_name}_executable")
    sample_rust_filename = f"test{sample_test_number}.rs"
    sample_output_dir = "/output"

    forbidden_crates = cpp_to_rust_mapping.get(sample_repo_name, "none")

    sample_prompt = f"""
You are an expert C++ to Rust migration engineer. Read the following C++ source code:

--- Source ({os.path.join(CONTAINER_DATASET_ROOT, sample_relative_path)}) ---
{sample_cpp_code}
---

Requirements:
1. **Environment**: Write pure Rust using the 2021 edition. Code must compile with `rustc` or as a Cargo project.

2. **CLI arguments**: The Rust binary must accept exactly the same command-line arguments as the C++ binary (same names, defaults, and required fields). Parse args via `std::env::args()`.

3. **Logic and output**: Algorithm logic, numeric precision, and string formatting must exactly match the C++ source. `println!` output must be byte-for-byte identical to `std::cout` output.

4. **Zero external dependencies**: Do NOT use any crates from crates.io (only `std`). Forbidden crates for this repo: {forbidden_crates}. Implement all functionality from scratch using the standard library.

5. **Project structure**: Create a complete Cargo project in `{sample_output_dir}`. Organize library code into modules. Place the entry test file `{sample_rust_filename}` in the package root `{sample_output_dir}`.

6. **Black-box implementation**: Do not read the C++ library source. Infer behavior from the interface, then re-implement using `std`.

7. **Output**:
   - Create and implement library files inside `{sample_output_dir}`.
   - Save the entry file to `{sample_output_dir}/{sample_rust_filename}`.
   - Compile and produce an executable at `{sample_output_dir}/{sample_rust_filename}` (by running `rustc {sample_rust_filename}` or `cargo build --release`).

Hint: `{sample_executable_path}` is the compiled C++ binary — use it to debug with any arguments.
"""

    print("="*60)
    print("Sample Prompt (first task's prompt):")
    print("="*60)
    print(sample_prompt)
    print("="*60)

    # Press Enter to continue, or 'q' to quit
    s = input("\nPress Enter to continue, or 'q' to quit: ")
    # if s.lower() == 'q':
    #     print("Exiting program")
    #     return

    # Process all tasks
    start_time = time.time()

    print(f"\n[START] Starting {num_processes} concurrent processes for evaluation...")

    progress_file = os.path.join(host_output_root, "progress.json")

    with Manager() as manager:
        lock = manager.Lock()
        shared_results = manager.list()

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            future_to_task = {
                executor.submit(
                    process_single_task,
                    task["cpp_path"],
                    task["relative_path"],
                    task["repo_name"],
                    task["test_number"],
                    packages_root,
                    host_output_root,
                    actual_name,
                ): task for task in tasks
            }

            for i, future in enumerate(as_completed(future_to_task), 1):
                try:
                    result = future.result()
                except Exception as e:
                    task = future_to_task[future]
                    print(f"Worker process crashed: {task['relative_path']} - {e}")
                    result = {
                        "success": False,
                        "relative_path": task['relative_path'],
                        "error": str(e)
                    }

                shared_results.append(result)
                print(f"\n[PROGRESS] [{i}/{len(tasks)}] Completed: {result['relative_path']}")

                # Save progress every 5 tasks
                if i % 5 == 0:
                    save_progress(progress_file, len(tasks), list(shared_results))

        # Final save progress
        save_progress(progress_file, len(tasks), list(shared_results))
        results = list(shared_results)

    # Statistics results
    elapsed_time = time.time() - start_time
    total_input_tokens = 0
    total_output_tokens = 0
    processed_count = 0
    failed_count = 0
    skipped_count = 0

    for result in results:
        if result.get("success"):
            total_input_tokens += result.get("input_tokens", 0)
            total_output_tokens += result.get("output_tokens", 0)
            processed_count += 1
        elif result.get("status") == "skipped":
            skipped_count += 1
        else:
            failed_count += 1
            print(f"Processing failed: {result['relative_path']}, error: {result.get('error', 'Unknown')}")

    # Print total statistics
    print("\n" + "="*60)
    print("Token Usage Statistics")
    print("="*60)
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already succeeded): {skipped_count}")
    print(f"Processing failed: {failed_count}")
    print(f"Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"Average per task: {elapsed_time/len(tasks):.2f} seconds")
    print(f"Total Input Tokens:  {total_input_tokens:,}")
    print(f"Total Output Tokens: {total_output_tokens:,}")
    print(f"Total Tokens:        {total_input_tokens + total_output_tokens:,}")
    if processed_count > 0:
        print(f"Average per task Input:  {total_input_tokens/processed_count:,.0f}")
        print(f"Average per task Output: {total_output_tokens/processed_count:,.0f}")
    print("="*60)

    # Save token log
    save_token_log(
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        processed_count=processed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        log_dir=host_output_root,
    )


if __name__ == "__main__":

    print(f"[CONFIG] Using {args.num_processes} concurrent processes for evaluation")
    print(f"[CONFIG] Model: {model_name}")
    print(f"[CONFIG] Docker image: {DOCKER_IMAGE}")

    main(num_processes=args.num_processes)