import sys
import os
import pathlib
import re
import subprocess
import shutil
import time
import json
import multiprocessing as mp
from multiprocessing import Pool, Manager
import posixpath
import tempfile

# Add current directory to path to import run_terminal_agent
sys.path.insert(0, os.path.dirname(__file__))
from run_terminal_agent import run_reasoning_agent

model_name = os.getenv("MODEL_NAME", "deepseek-v3.2")
actual_name = os.getenv("MODEL_NAME", "deepseek-v3.2")

valid_ids = ['boltons/test10.py', 'fractions/test14.py', 'deepdiff/test16.py', 'bech32/test4.py', 'idna/test13.py', 'base58/test6.py', 'bech32/test12.py', 'canonicaljson/test20.py', 'idna/test6.py', 'jsonschema/test7.py', 'schedule/test9.py', 'bidict/test5.py', 'mpmath/test4.py', 'furl/test5.py', 'furl/test11.py', 'bidict/test13.py', 'bech32/test2.py', 'networkx/test14.py', 'yaml/test16.py', 'bech32/test9.py', 'idna/test9.py', 'base58/test1.py', 'networkx/test5.py', 'moneyed/test6.py', 'bencoder/test7.py', 'pyaes/test10.py', 'markdown/test13.py', 'networkx/test4.py', 'bencoder/test15.py', 'jsonschema/test15.py', 'networkx/test16.py', 'markdown/test19.py', 'base58/test2.py', 'rsa/test15.py', 'construct/test12.py', 'rsa/test19.py', 'whoosh/test2.py', 'moneyed/test17.py', 'networkx/test13.py', 'networkx/test7.py', 'mpmath/test12.py', 'rsa/test8.py', 'canonicaljson/test14.py', 'networkx/test3.py', 'base58/test7.py', 'boltons/test14.py', 'boltons/test3.py', 'idna/test4.py', 'boltons/test11.py', 'mpmath/test1.py', 'base58/test19.py', 'moneyed/test3.py', 'bech32/test13.py', 'construct/test16.py', 'pyaes/test17.py', 'sqlparse/test4.py', 'jose/test7.py', 'idna/test18.py', 'jose/test13.py', 'whoosh/test7.py', 'bidict/test10.py', 'pyaes/test2.py', 'whoosh/test6.py', 'yaml/test2.py', 'deepdiff/test3.py', 'canonicaljson/test8.py', 'whoosh/test1.py', 'bencoder/test6.py', 'bidict/test17.py', 'moneyed/test15.py', 'pyaes/test12.py', 'idna/test11.py', 'deepdiff/test18.py', 'sqlparse/test2.py', 'rsa/test5.py', 'yaml/test11.py', 'canonicaljson/test11.py', 'schedule/test13.py', 'schedule/test2.py', 'jsonschema/test8.py', 'mpmath/test19.py', 'pyaes/test9.py', 'pyaes/test19.py', 'fractions/test15.py', 'markdown/test11.py', 'bidict/test16.py', 'construct/test20.py', 'yaml/test6.py', 'mpmath/test13.py', 'mpmath/test18.py', 'idna/test12.py', 'bech32/test15.py', 'yaml/test12.py', 'boltons/test15.py', 'deepdiff/test10.py', 'rsa/test16.py', 'boltons/test4.py', 'furl/test12.py', 'moneyed/test12.py', 'whoosh/test20.py', 'schedule/test19.py', 'bidict/test3.py', 'base58/test17.py', 'fractions/test2.py', 'moneyed/test7.py', 'whoosh/test3.py', 'mpmath/test7.py', 'construct/test17.py', 'idna/test15.py', 'mpmath/test17.py', 'markdown/test4.py', 'mpmath/test11.py', 'bech32/test1.py', 'bidict/test12.py', 'bencoder/test5.py', 'mpmath/test16.py', 'jose/test15.py', 'pyaes/test4.py', 'canonicaljson/test1.py', 'bech32/test14.py', 'moneyed/test14.py', 'jsonschema/test9.py', 'fractions/test19.py', 'construct/test19.py', 'yaml/test10.py', 'canonicaljson/test17.py', 'markdown/test7.py', 'schedule/test10.py', 'jsonschema/test10.py', 'mpmath/test15.py', 'bencoder/test8.py', 'bidict/test8.py', 'canonicaljson/test9.py', 'bencoder/test18.py', 'base58/test15.py', 'moneyed/test9.py', 'boltons/test6.py', 'boltons/test5.py', 'fractions/test6.py', 'jose/test9.py', 'yaml/test5.py', 'moneyed/test11.py', 'yaml/test7.py', 'bidict/test14.py', 'fractions/test5.py', 'boltons/test17.py', 'jsonschema/test20.py', 'deepdiff/test4.py', 'construct/test15.py', 'construct/test7.py', 'idna/test17.py', 'networkx/test6.py', 'whoosh/test18.py', 'jsonschema/test14.py', 'fractions/test4.py', 'jose/test10.py', 'rsa/test7.py', 'canonicaljson/test13.py', 'furl/test6.py', 'canonicaljson/test5.py', 'boltons/test7.py', 'yaml/test15.py', 'base58/test13.py', 'bencoder/test3.py', 'pyaes/test11.py', 'pbkdf2/test16.py', 'bech32/test3.py', 'jose/test12.py', 'moneyed/test19.py', 'deepdiff/test1.py', 'boltons/test9.py', 'markdown/test14.py', 'pyaes/test8.py', 'bencoder/test17.py', 'fractions/test1.py', 'schedule/test3.py', 'jose/test1.py', 'idna/test16.py', 'bech32/test11.py', 'jose/test6.py', 'base58/test9.py', 'mpmath/test3.py', 'bencoder/test13.py', 'bidict/test11.py', 'idna/test8.py', 'schedule/test6.py', 'bidict/test7.py', 'pbkdf2/test15.py', 'moneyed/test2.py', 'pbkdf2/test11.py', 'rsa/test11.py', 'jsonschema/test18.py', 'jsonschema/test6.py', 'base58/test12.py', 'yaml/test18.py', 'bencoder/test2.py', 'construct/test5.py', 'furl/test10.py', 'boltons/test1.py', 'deepdiff/test11.py', 'bech32/test8.py', 'furl/test9.py', 'fractions/test16.py', 'whoosh/test9.py', 'schedule/test18.py', 'bech32/test16.py', 'base58/test16.py', 'whoosh/test15.py', 'jsonschema/test2.py', 'schedule/test14.py', 'moneyed/test13.py', 'yaml/test9.py', 'jose/test19.py', 'bidict/test6.py', 'markdown/test12.py', 'base58/test14.py', 'whoosh/test4.py', 'bidict/test1.py', 'pyaes/test13.py', 'idna/test19.py', 'networkx/test15.py', 'idna/test2.py', 'pyaes/test7.py', 'bidict/test18.py', 'whoosh/test17.py', 'bencoder/test10.py', 'yaml/test20.py', 'bidict/test20.py', 'pyaes/test14.py', 'bencoder/test9.py', 'whoosh/test11.py', 'base58/test20.py', 'markdown/test16.py', 'furl/test3.py', 'furl/test2.py', 'yaml/test1.py', 'moneyed/test18.py', 'moneyed/test5.py', 'sqlparse/test9.py', 'whoosh/test14.py', 'schedule/test20.py', 'base58/test8.py', 'sqlparse/test16.py', 'idna/test7.py', 'idna/test20.py', 'pbkdf2/test13.py', 'furl/test4.py', 'construct/test18.py', 'jsonschema/test5.py', 'schedule/test12.py', 'bidict/test19.py', 'furl/test7.py', 'construct/test3.py', 'deepdiff/test15.py', 'markdown/test1.py', 'schedule/test4.py', 'jsonschema/test1.py', 'construct/test10.py', 'schedule/test16.py', 'construct/test14.py', 'bencoder/test11.py', 'schedule/test5.py', 'boltons/test19.py', 'bencoder/test14.py', 'jsonschema/test13.py', 'fractions/test13.py', 'schedule/test1.py', 'base58/test4.py', 'jose/test17.py', 'jsonschema/test19.py', 'bech32/test7.py', 'mpmath/test5.py', 'canonicaljson/test18.py', 'jose/test3.py', 'furl/test13.py', 'base58/test18.py', 'fractions/test20.py', 'jsonschema/test4.py', 'markdown/test15.py', 'markdown/test9.py', 'sqlparse/test3.py', 'boltons/test13.py', 'markdown/test6.py', 'markdown/test3.py', 'rsa/test18.py', 'fractions/test3.py', 'pyaes/test15.py', 'bencoder/test16.py', 'boltons/test2.py', 'fractions/test17.py', 'jose/test2.py', 'canonicaljson/test3.py', 'canonicaljson/test7.py', 'networkx/test2.py', 'pbkdf2/test7.py', 'yaml/test14.py', 'mpmath/test6.py', 'pyaes/test18.py', 'whoosh/test19.py', 'jsonschema/test12.py', 'moneyed/test1.py', 'pbkdf2/test14.py', 'whoosh/test16.py', 'deepdiff/test2.py', 'bencoder/test1.py', 'networkx/test17.py', 'construct/test1.py', 'pyaes/test16.py', 'markdown/test8.py', 'markdown/test17.py', 'canonicaljson/test15.py', 'construct/test6.py', 'jose/test4.py', 'pbkdf2/test8.py', 'bencoder/test12.py', 'rsa/test2.py', 'networkx/test20.py', 'canonicaljson/test16.py', 'construct/test8.py', 'pyaes/test5.py', 'yaml/test8.py', 'sqlparse/test10.py', 'idna/test3.py', 'schedule/test11.py', 'canonicaljson/test10.py', 'markdown/test2.py', 'mpmath/test9.py', 'bidict/test15.py', 'markdown/test5.py', 'canonicaljson/test2.py', 'boltons/test12.py', 'whoosh/test8.py', 'moneyed/test10.py', 'jsonschema/test11.py', 'canonicaljson/test19.py', 'pyaes/test6.py', 'pbkdf2/test1.py', 'pbkdf2/test4.py', 'sqlparse/test7.py', 'bidict/test4.py', 'furl/test1.py', 'markdown/test10.py', 'yaml/test17.py', 'base58/test11.py', 'jose/test8.py', 'rsa/test17.py', 'yaml/test4.py', 'idna/test10.py', 'furl/test8.py', 'construct/test4.py', 'jsonschema/test16.py', 'fractions/test12.py', 'bech32/test10.py', 'canonicaljson/test4.py', 'rsa/test10.py', 'bencoder/test4.py', 'bidict/test9.py', 'construct/test2.py', 'yaml/test19.py', 'pbkdf2/test2.py', 'fractions/test7.py', 'pbkdf2/test10.py', 'whoosh/test10.py', 'mpmath/test14.py', 'bidict/test2.py', 'idna/test1.py', 'networkx/test1.py', 'mpmath/test8.py', 'idna/test14.py', 'jsonschema/test3.py', 'base58/test10.py', 'deepdiff/test6.py', 'idna/test5.py', 'deepdiff/test12.py', 'moneyed/test8.py', 'canonicaljson/test6.py', 'fractions/test8.py', 'jose/test16.py', 'fractions/test9.py', 'mpmath/test10.py', 'networkx/test11.py', 'fractions/test11.py', 'markdown/test20.py', 'markdown/test18.py', 'bencoder/test19.py', 'base58/test3.py', 'yaml/test13.py', 'jose/test11.py', 'pbkdf2/test6.py', 'canonicaljson/test12.py', 'networkx/test10.py', 'schedule/test7.py', 'bech32/test17.py', 'moneyed/test20.py', 'bech32/test6.py', 'mpmath/test2.py', 'whoosh/test5.py', 'bech32/test5.py', 'moneyed/test16.py', 'base58/test5.py']

excluded_ids = ['pyaes', 'yaml', 'idna', 'markdown']

python_to_js_mapping = {
    # Encoding & Hashing: Map to native Buffer/Uint8Array or Web Crypto API
    "base58": "Uint8Array / Buffer (Manual Base58 Encoding Logic)",
    "bech32": "Uint8Array / DataView (Manual Bech32 Encoding Logic)",
    "bencoder": "Uint8Array / ArrayBuffer (Manual Bencode logic)",
    "rlp": "Uint8Array / Buffer (Recursive Length Prefix logic)",
    "canonicaljson": "JSON.stringify (Custom sorting and normalization logic)",

    # Data Structures & Bit Operations: Map to native binary processing
    "bidict": "Map (Dual-direction key/value management)",
    "bitarray": "Uint8Array / BigInt / Bitwise Operators",
    "bitstring": "Buffer / Uint8Array / DataView",
    "construct": "DataView / ArrayBuffer (Manual Struct Parsing)",

    # Cryptography: Map to crypto module, enforce handling raw bytes and algorithm logic
    "ecdsa": "node:crypto (SubtleCrypto / createSign / createVerify)",
    "rsa": "node:crypto (KeyObject / publicEncrypt / privateDecrypt)",
    "jose": "node:crypto (JWT/JWE manual construction with HMAC/RSA)",
    "pbkdf2": "node:crypto (crypto.pbkdf2 / crypto.pbkdf2Sync)",
    "pyaes": "node:crypto (Cipher / Decipher / createCipheriv)",

    # Math & Standards: Map to built-in objects or BigInt
    "fractions": "BigInt / Number (Manual Rational Number logic)",
    "mpmath": "BigInt (Arbitrary-precision arithmetic logic)",
    "moneyed": "Intl.NumberFormat / BigInt",
    "idna": "url (URL class) / punycode (Built-in module)",

    # Parsing: Map to more basic parsers or regex logic
    "markdown": "RegExp / String Manipulation (Manual AST Construction)",
    "sqlparse": "RegExp / String (Manual Lexer/Tokenizer logic)",
    "yaml": "JSON / RegExp (Manual YAML to Object mapping)"
}

# Host path configuration
HOST_DATASET_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Py2JS", "dataset")
HOST_ARENA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Py2JS", "output", actual_name)

# Docker internal path configuration
CONTAINER_WORKSPACE = "/workspace"
CONTAINER_DATASET_ROOT = f"{CONTAINER_WORKSPACE}/dataset"
CONTAINER_OUTPUT_ROOT = f"{CONTAINER_WORKSPACE}/output/{actual_name}"

# Docker image configuration
DOCKER_IMAGE = os.getenv("REPOZERO_DOCKER_IMAGE", "ghcr.io/jessezzzzz/repoarena-new:latest")


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
    success, stdout, stderr = run_docker_command(f"docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}}' | grep '^{image_name}$'", timeout=10)
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


def create_task_container(task_name, py_path=None):
    """
    Create temporary Docker container for single task

    Args:
        task_name: Task name (e.g., base58/test1.py -> base58-test1)
        py_path: Python file host path for copying into container

    Returns:
        New container name, or None on failure
    """
    new_container_name = f"repoarena-{task_name.replace('/', '-').replace('.py', '')}"

    # Step 1: Ensure image exists
    if not ensure_image_exists(DOCKER_IMAGE):
        return None

    # Step 2: Check if container exists, delete if so
    exists, stdout, stderr = run_docker_command(f"docker ps -a --filter name={new_container_name} --format '{{{{.Names}}}}'")
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
    success, stdout, stderr = run_docker_command(f"docker exec {new_container_name} cat /sys/class/net/lo/iflink", timeout=10)
    if success and stdout.strip() == "1":
        print(f"[OK] Container {new_container_name} network isolation normal (lo only)")

    # Copy py file and pre-compiled exe file into container
    if py_path:
        py_filename = os.path.basename(py_path)
        module_name = py_filename.replace(".py", "")

        # Find pre-compiled exe file (named testX_executable in same directory as source file)
        host_py_dir = os.path.dirname(py_path)
        exe_filename = f"{module_name}_executable"
        host_executable_path = os.path.join(host_py_dir, exe_filename)

        if not os.path.exists(host_executable_path):
            print(f"[WARNING] Pre-compiled file not found: {host_executable_path}")
            return None

        # Container internal paths
        container_dataset_dir = CONTAINER_DATASET_ROOT
        container_executable_path = posixpath.join(container_dataset_dir, exe_filename)
        container_py_path = posixpath.join(container_dataset_dir, py_filename)

        # Ensure container directory exists
        run_docker_command(f"docker exec {new_container_name} mkdir -p {container_dataset_dir} 2>&1", timeout=10)

        # Copy executable file
        success, _, _ = run_docker_cp(host_executable_path, new_container_name, container_executable_path, timeout=10)
        if success:
            print(f"[OK] Container {new_container_name} executable copied to {container_executable_path}")
            # Set executable permission
            run_docker_command(f"docker exec {new_container_name} chmod +x {container_executable_path} 2>&1", timeout=10)
        else:
            print(f"[WARNING] Container {new_container_name} failed to copy executable file")
            return None

        # Copy source file (agent can view)
        run_docker_cp(py_path, new_container_name, container_py_path, timeout=10)
        print(f"[OK] Container {new_container_name} source code copied to {container_py_path}")

    print(f"[OK] Created container: {new_container_name}")
    return new_container_name


def cleanup_task_container(container_name):
    """Cleanup task container"""
    run_docker_command(f"docker rm -f {container_name}")


def process_single_task_wrapper(args):
    """
    Wrapper function for multiprocessing pool calls

    Args:
        args: Tuple containing (py_path, relative_path, progress_dict, lock)

    Returns:
        Processing result dictionary
    """
    py_path, relative_path, progress_dict, lock = args
    return process_single_task(py_path, relative_path, progress_dict, lock)


def process_single_task(py_path, relative_path, progress_dict=None, lock=None):
    """
    Process single task

    Args:
        py_path: Host absolute path of Python file
        relative_path: Relative path to dataset (e.g., base58/test1.py)
        progress_dict: Shared progress dictionary (for multiprocessing)
        lock: Process lock (for multiprocessing)

    Returns:
        Processing result dictionary
    """
    try:
        # Generate task name
        task_name = relative_path.replace('.py', '')
        python_package = task_name.split('/')[0]

        # Ensure current task's pkg directory exists
        pkg_name = relative_path.replace('.py', '_pkg')
        host_pkg_dir = os.path.join(HOST_ARENA_ROOT, "packages", pkg_name)
        if not os.path.exists(host_pkg_dir):
            os.makedirs(host_pkg_dir, exist_ok=True)

        # Create task container
        task_container = create_task_container(task_name, py_path=py_path)
        if not task_container:
            return {
                "success": False,
                "relative_path": relative_path,
                "error": "Failed to create task container"
            }

        try:
            # Container internal output path (use simple path to avoid tmpfs issues)
            container_output_dir = "/output"

            print(f"[OK] Container {task_container} ready")

            # Read Python code
            with open(py_path, "r", encoding="utf-8") as f:
                py_code = f.read()

            # Container internal executable path
            py_filename = os.path.basename(py_path)
            module_name = py_filename.replace(".py", "")
            exe_filename = f"{module_name}_executable"
            container_executable_path = posixpath.join(CONTAINER_DATASET_ROOT, exe_filename)

            # Build prompt for Agent
            prompt = f"""
You are a senior cross-language migration expert (Python to Node.js). Please read the following Python code:

--- Source Code ({os.path.join(CONTAINER_DATASET_ROOT, relative_path)}) ---
{py_code}
---

Task Requirements:
1. **Environment & Module Specifications**:
- Write pure JavaScript code for Node.js runtime.
- **ES Modules (ESM) specification is mandatory**: You MUST use `import` to import modules and `export` to export modules. **`require()` and `module.exports` are strictly prohibited**.
- **File suffix requirement**: To ensure Node.js correctly recognizes ESM, generated library files and entry test files MUST use the **`.mjs`** suffix.

2. **Command Line Argument Alignment**:
- The JS file must have **exactly the same** command-line argument passing as the above Python file (parameter names, default values, and required fields must all match).
- You need to manually parse `process.argv`. Ensure `node test.mjs --arg val` behaves identically to `{container_executable_path} --arg val` in argument parsing logic.

3. **Logic & Output Alignment**:
- Algorithm logic, numerical calculation precision, and string formatting must be completely consistent with the original Python file.
- Ensure `console.log` output content (including spaces and newlines) matches Python's `print` results character by character.

4. **Zero External Dependencies**:
- **Any npm external modules are prohibited** (such as yargs, argparse, etc.).
- **Prohibit importing external modules via import; only import local files**. Otherwise, the answer will be considered invalid.
- **Prohibit embedding Python scripts**. Must use Node.js native built-in modules (such as `node:fs`, `node:path`, `node:url`, etc.).

5. **Engineering Structure & ESM Features**:
- Generate library files and entry test files in `{container_output_dir}`.
- **Hierarchical organization**: Libraries must be split into multiple modules by functionality and expose interfaces through `export`.
- **Note**: In ESM, `import` statements must include complete file suffixes (for example: `import {{ x }} from './utils.mjs'`).
- **Path handling**: Your workspace is `{CONTAINER_WORKSPACE}`, but all generated code must be saved to the `{container_output_dir}` directory.

6. **Black Box Implementation**:
- You cannot view the internal source code of Python native packages; you can only reimplement logic in JS through interface behavior.
- Strictly prohibit calling or mentioning any interface of `{python_to_js_mapping.get(python_package, 'JS external library')}`.

7. **Execution Method**:
- You can observe the behavior of the Python code by running the pre-compiled executable: `{container_executable_path} --arg value`
- **Important**: Do not use the `python` command; run the executable directly. The executable already includes all necessary dependencies, so there's no need to worry about environment issues.

Hint: Please first output the hierarchical code of library files (using .mjs), and finally output the code of the entry test file `{task_name.split("/")[-1]}.mjs` in {container_output_dir}.
"""

            print(f"\n{'='*60}")
            print(f"Processing: {relative_path}")
            print(f"Container: {task_container}")
            print(f"{'='*60}\n")

            # Call Agent to execute task inside Docker container
            token_info = run_reasoning_agent(prompt, container_name=task_container, model_name=model_name)

            # Get token statistics
            input_tokens = token_info.get("input_tokens", 0) if token_info else 0
            output_tokens = token_info.get("output_tokens", 0) if token_info else 0

            print(f"\n[Completed] {relative_path} | Input={input_tokens}, Output={output_tokens}")

            # Copy output files from container to host
            print(f"[COPY] Copying output files to host: {host_pkg_dir}")
            success, stdout, stderr = run_docker_command(
                f"docker cp {task_container}:{container_output_dir}/. {host_pkg_dir}",
                timeout=30
            )
            if success:
                print(f"[OK] Output files synced to: {host_pkg_dir}")
                # List copied files
                files = os.listdir(host_pkg_dir) if os.path.exists(host_pkg_dir) else []
                if files:
                    print(f"   Generated files: {files}")
            else:
                print(f"[WARNING] Failed to copy output: {stderr}")

            return {
                "success": True,
                "relative_path": relative_path,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "container": task_container,
                "output_dir": host_pkg_dir
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


def save_progress(progress_file, total, results):
    """Save progress to file"""
    with open(progress_file, "w") as f:
        json.dump({
            "total": total,
            "processed": len(results),
            "results": results
        }, f, indent=2)


def main(num_processes=4):
    global model_name
    global actual_name
    global python_to_js_mapping

    # Ensure output directory exists
    if not os.path.exists(HOST_ARENA_ROOT):
        os.makedirs(HOST_ARENA_ROOT)

    # Ensure packages directory exists
    packages_dir = os.path.join(HOST_ARENA_ROOT, "packages")
    if not os.path.exists(packages_dir):
        os.makedirs(packages_dir)

    # Collect all tasks to process
    tasks = []
    for root, dirs, files in os.walk(HOST_DATASET_ROOT):
        files = sorted(files)

        for file in files:
            if file.endswith(".py"):
                py_path = os.path.join(root, file)
                relative_path = os.path.relpath(py_path, HOST_DATASET_ROOT)

                # Skip existing files (check if corresponding mjs file exists in pkg directory)
                pkg_name = relative_path.replace('.py', '_pkg')
                mjs_filename = relative_path.replace('.py', '.mjs').split('/')[-1]
                pkg_path = os.path.join(packages_dir, pkg_name, mjs_filename)
                if os.path.exists(pkg_path):
                    print(f"[SKIP] {pkg_path} already exists, skipping")
                    continue

                # Check if in valid ID list
                if not relative_path in valid_ids:
                    continue

                tasks.append((py_path, relative_path))

    if not tasks:
        print("No files to process")
        return

    print(f"Found {len(tasks)} files to process\n")

    # Show first task's prompt for confirmation
    sample_py_path, sample_relative_path = tasks[0]
    with open(sample_py_path, "r", encoding="utf-8") as f:
        sample_py_code = f.read()
    python_package = sample_relative_path.split('/')[0]
    pkg_name = sample_relative_path.replace('.py', '_pkg')
    container_output_dir = "/output"
    task_name = sample_relative_path.replace('.py', '')

    # Sample executable path
    sample_module_name = os.path.basename(sample_py_path).replace('.py', '')
    sample_executable_path = posixpath.join(CONTAINER_DATASET_ROOT, f"{sample_module_name}_executable")

    sample_prompt = f"""
You are a senior cross-language migration expert (Python to Node.js). Please read the following Python code:

--- Source Code ({os.path.join(CONTAINER_DATASET_ROOT, sample_relative_path)}) ---
{sample_py_code}
---

Task Requirements:
1. **Environment & Module Specifications**:
- Write pure JavaScript code for Node.js runtime.
- **ES Modules (ESM) specification is mandatory**: You MUST use `import` to import modules and `export` to export modules. **`require()` and `module.exports` are strictly prohibited**.
- **File suffix requirement**: To ensure Node.js correctly recognizes ESM, generated library files and entry test files MUST use the **`.mjs`** suffix.

2. **Command Line Argument Alignment**:
- The JS file must have **exactly the same** command-line argument passing as the above Python file (parameter names, default values, and required fields must all match).
- You need to manually parse `process.argv`. Ensure `node test.mjs --arg val` behaves identically to `{sample_executable_path} --arg val` in argument parsing logic.

3. **Logic & Output Alignment**:
- Algorithm logic, numerical calculation precision, and string formatting must be completely consistent with the original Python file.
- Ensure `console.log` output content (including spaces and newlines) matches Python's `print` results character by character.

4. **Zero External Dependencies**:
- **Any npm external modules are prohibited** (such as yargs, argparse, etc.).
- **Prohibit importing external modules via import; only import local files**. Otherwise, the answer will be considered invalid.
- **Prohibit embedding Python scripts**. Must use Node.js native built-in modules (such as `node:fs`, `node:path`, `node:url`, etc.).

5. **Engineering Structure & ESM Features**:
- Generate library files and entry test files in `{container_output_dir}`.
- **Hierarchical organization**: Libraries must be split into multiple modules by functionality and expose interfaces through `export`.
- **Note**: In ESM, `import` statements must include complete file suffixes (for example: `import {{ x }} from './utils.mjs'`).
- **Path handling**: Your workspace is `{CONTAINER_WORKSPACE}`, but all generated code must be saved to the `{container_output_dir}` directory.

6. **Black Box Implementation**:
- You cannot view the internal source code of Python native packages; you can only reimplement logic in JS through interface behavior.
- Strictly prohibit calling or mentioning any interface of `{python_to_js_mapping.get(python_package, 'JS external library')}`.

7. **Execution Method**:
- You can observe the behavior of the Python code by running the pre-compiled executable: `{sample_executable_path} --arg value`
- **Important**: Do not use the `python` command; run the executable directly. The executable already includes all necessary dependencies, so there's no need to worry about environment issues.

Hint: Please first output the hierarchical code of library files (using .mjs), and finally output the code of the entry test file `{task_name}.mjs` in {container_output_dir}.
"""
    print("="*60)
    print("Sample Prompt (first task's prompt):")
    print("="*60)
    print(sample_prompt)
    print("="*60)

    s = input("\nPress Enter to continue, or 'q' to quit: ")
    if s.lower() == 'q':
        print("Exiting program")
        return

    # Process all tasks
    start_time = time.time()

    # Use multiprocessing pool for concurrent task processing
    print(f"\n[START] Starting {num_processes} concurrent processes for evaluation...")

    # Create shared variables for progress tracking
    with Manager() as manager:
        shared_results = manager.list()
        shared_processed = manager.Value('i', 0)

        # Prepare task arguments
        task_args = [(py_path, relative_path, shared_results, shared_processed)
                    for py_path, relative_path in tasks]

        progress_file = os.path.join(HOST_ARENA_ROOT, "progress.json")

        # Use process pool to process tasks
        with Pool(processes=num_processes) as pool:
            # Use imap_unordered to get results and show progress
            for i, result in enumerate(pool.imap_unordered(process_single_task_wrapper, task_args), 1):
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
    error_count = 0

    for result in results:
        if result["success"]:
            total_input_tokens += result.get("input_tokens", 0)
            total_output_tokens += result.get("output_tokens", 0)
            processed_count += 1
        else:
            error_count += 1
            print(f"Processing failed: {result['relative_path']}, error: {result.get('error', 'Unknown')}")

    # Print total statistics
    print("\n" + "="*60)
    print("Token Usage Statistics")
    print("="*60)
    print(f"Successfully processed: {processed_count}")
    print(f"Processing failed: {error_count}")
    print(f"Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"Average per task: {elapsed_time/len(tasks):.2f} seconds")
    print(f"Total Input Tokens:  {total_input_tokens:,}")
    print(f"Total Output Tokens: {total_output_tokens:,}")
    print(f"Total Tokens:        {total_input_tokens + total_output_tokens:,}")
    if processed_count > 0:
        print(f"Average per task Input:  {total_input_tokens/processed_count:,.0f}")
        print(f"Average per task Output: {total_output_tokens/processed_count:,.0f}")
    print("="*60)


if __name__ == "__main__":
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

    print(f"[CONFIG] Using {args.num_processes} concurrent processes for evaluation")
    print(f"[CONFIG] Model: {model_name}")
    print(f"[CONFIG] Docker image: {DOCKER_IMAGE}")
    res = main(num_processes=args.num_processes)
