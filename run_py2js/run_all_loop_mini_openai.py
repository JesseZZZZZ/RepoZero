import os
import json
import subprocess
import tempfile
from multiprocessing import Pool
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
model_name = "deepseek-v3.1-250821"
api_base = os.environ.get("QIANFAN_API_URL", "https://qianfan.baidubce.com/v2")
provider = "openai"
num_processes = 10

MINI_BIN = os.environ.get("MINI_SWE_AGENT_BIN", "mini")

python_to_js_mapping = {
    "base58": "Uint8Array / Buffer (Manual Base58 Encoding Logic)",
    "bech32": "Uint8Array / DataView (Manual Bech32 Encoding Logic)",
    "bencoder": "Uint8Array / ArrayBuffer (Manual Bencode logic)",
    "rlp": "Uint8Array / Buffer (Recursive Length Prefix logic)",
    "canonicaljson": "JSON.stringify (Custom sorting and normalization logic)",
    "bidict": "Map (Dual-direction key/value management)",
    "bitarray": "Uint8Array / BigInt / Bitwise Operators",
    "bitstring": "Buffer / Uint8Array / DataView",
    "construct": "DataView / ArrayBuffer (Manual Struct Parsing)",
    "ecdsa": "node:crypto (SubtleCrypto / createSign / createVerify)",
    "rsa": "node:crypto (KeyObject / publicEncrypt / privateDecrypt)",
    "jose": "node:crypto (JWT/JWE manual construction with HMAC/RSA)",
    "pbkdf2": "node:crypto (crypto.pbkdf2 / crypto.pbkdf2Sync)",
    "pyaes": "node:crypto (Cipher / Decipher / createCipheriv)",
    "fractions": "BigInt / Number (Manual Rational Number logic)",
    "mpmath": "BigInt (Arbitrary-precision arithmetic logic)",
    "moneyed": "Intl.NumberFormat / BigInt",
    "idna": "url (URL class) / punycode (Built-in module)",
    "markdown": "RegExp / String Manipulation (Manual AST Construction)",
    "sqlparse": "RegExp / String (Manual Lexer/Tokenizer logic)",
    "yaml": "JSON / RegExp (Manual YAML to Object mapping)",
}


def run_mini_swe_agent(prompt, model_name=None, api_base=None, provider=None):
    """Run mini-swe-agent and wait for completion."""
    print(f"\n[mini-swe-agent] Model: {model_name}, API: {api_base}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        shell_cmd = (
            f"cd {str(REPO_ROOT / 'Py2JS')!r} && MSWEA_COST_TRACKING=ignore_errors "
            f"{MINI_BIN} --model openai/{model_name} -y --exit-immediately "
            f"-t {prompt_file!r} --custom-llm-provider litellm --api-base {api_base}"
        )
        process = subprocess.Popen(
            shell_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while True:
            line = process.stdout.readline()
            if not line:
                break
            print(line, end="", flush=True)
        process.wait()
        stderr_output = process.stderr.read()
        if process.returncode != 0:
            print(f"\nmini-swe-agent failed (exit code: {process.returncode})")
            if stderr_output:
                print(f"STDERR: {stderr_output}")
            return False, f"Exit code {process.returncode}: {stderr_output}"
        print("\nmini-swe-agent succeeded.")
        return True, None
    except Exception as e:
        print(f"\nmini-swe-agent exception: {e}")
        return False, str(e)
    finally:
        try:
            os.unlink(prompt_file)
        except Exception:
            pass


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": 1}


def build_prompt(dataset_root, relative_path, py_code, js_output_path, output_base, python_package, max_retries):
    forbidden = python_to_js_mapping.get(python_package, "Unknown Python Package")
    mjs_path = js_output_path.replace(".cjs", ".mjs")
    return f"""
You are an expert cross-language migration engineer (Python to Node.js). Read the following Python source code:

--- Source ({os.path.join(dataset_root, relative_path)}) ---
{py_code}
---

Requirements:
1. **Environment**: Write pure JavaScript for Node.js using ES Modules (ESM). Use `import`/`export`. Do NOT use `require()` or `module.exports`.
   - All generated library and entry files must use the `.mjs` suffix.

2. **CLI arguments**: The JS file must accept exactly the same command-line arguments as the Python file (same names, defaults, required fields). Parse via `process.argv`. `node test.mjs --arg val` must behave identically to `python test.py --arg val`.

3. **Logic and output**: Algorithm logic, numeric precision, and string formatting must exactly match the Python source. `console.log` output must be byte-for-byte identical to Python `print` output.

4. **Zero external dependencies**: Do NOT use any npm packages (e.g., yargs, argparse). Only import local files. Use only Node.js built-in modules (e.g., `node:fs`, `node:path`, `node:url`).

5. **Project structure**: Generate library files in `{output_base}/packages/{relative_path.replace(".py", "_pkg")}`. Split library code into modules with `export`. In ESM, `import` statements must include full file extensions (e.g., `import {{ x }} from './utils.mjs'`). Working directory: `{output_base}`.

6. **Black-box implementation**: Do not read Python library source. Infer behavior from the interface and re-implement in JS. Do NOT reference `{forbidden}`.

Output library files first (.mjs), then the entry test file `{mjs_path}`.
"""


def process_single_file(task_info):
    py_path, relative_path, dataset_root, output_base, model_name, api_base, provider, python_to_js_mapping, max_retries = task_info
    pid = os.getpid()

    js_output_path = os.path.join(output_base, "testfiles", relative_path.replace(".py", ".mjs"))
    test_cases_path = os.path.join(output_base, "test_cases", relative_path.replace(".py", ".json"))

    os.makedirs(os.path.dirname(js_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(test_cases_path), exist_ok=True)

    print(f"[PID {pid}] Processing: {relative_path}")

    with open(py_path, "r", encoding="utf-8") as f:
        py_code = f.read()

    python_package = relative_path.split("/")[0]
    full_prompt = build_prompt(dataset_root, relative_path, py_code, js_output_path, output_base, python_package, max_retries)

    # Step 1: Generate test cases
    gen_test_prompt = f"""
You are a test engineer. Read the following Python code and generate 5 different sets of command-line arguments to test its logic.
Cover: normal input, boundary values, and possible error inputs.

Source code:
{py_code}

Output a JSON array of strings only, e.g.: ["--input 1", "--input 10 --verbose", ""]
No explanations, no output values — only input argument strings.
"""
    print(f"[PID {pid}] Generating test cases...")
    run_mini_swe_agent(
        f"Read the code and save test parameters to {test_cases_path} as a JSON array:\n{gen_test_prompt}",
        model_name, api_base, provider,
    )
    try:
        with open(test_cases_path, "r") as f:
            test_cases = json.load(f)
    except Exception:
        test_cases = [""]

    # Step 2: Iterative solver loop
    fail_reason = ""
    for attempt in range(max_retries):
        print(f"[PID {pid}] Attempt {attempt + 1}/{max_retries}...")
        if attempt == 0:
            solver_prompt = full_prompt
        else:
            solver_prompt = (
                f"{full_prompt}\n\n"
                f"[IMPORTANT] Do not rewrite from scratch — fix the existing code.\n"
                f"Current path: {js_output_path}\n"
                f"Library path: {output_base}/packages/{relative_path.replace('.py', '_pkg')}\n"
                f"Previous failure:\n{fail_reason}"
            )
        run_mini_swe_agent(solver_prompt, model_name, api_base, provider)

        # Step 3: Validate
        all_passed = True
        fail_reason = ""
        for args in test_cases:
            py_res = run_command(f"python3 {py_path} {args}")
            if py_res["exit_code"] != 0:
                print(f"[PID {pid}]   [Skip] Test case '{args}' failed in Python, ignoring.")
                continue
            js_res = run_command(f"node {js_output_path} {args}")
            if py_res["stdout"] != js_res["stdout"]:
                all_passed = False
                fail_reason = (
                    f"Args '{args}' output mismatch.\n"
                    f"Python stdout:\n{py_res['stdout']}\n"
                    f"JS stdout:\n{js_res['stdout']}"
                )
                break
            if py_res["exit_code"] != js_res["exit_code"]:
                all_passed = False
                fail_reason = f"Args '{args}' exit code mismatch (Py:{py_res['exit_code']}, JS:{js_res['exit_code']})"
                break

        if all_passed:
            print(f"[PID {pid}] Validation passed: {relative_path}")
            return {"relative_path": relative_path, "status": "success", "error": None}
        else:
            print(f"[PID {pid}] Validation failed: {fail_reason}")
            py_code += f"\n\n# Previous failure feedback:\n# {fail_reason}"

    print(f"[PID {pid}] Giving up after {max_retries} attempts: {relative_path}")
    return {"relative_path": relative_path, "status": "failed", "error": fail_reason}


def collect_tasks(dataset_root, output_base, model_name, api_base, provider, python_to_js_mapping, max_retries):
    tasks = []
    for root, dirs, files in os.walk(dataset_root):
        for file in sorted(files):
            if not file.endswith(".py"):
                continue
            py_path = os.path.join(root, file)
            relative_path = os.path.relpath(py_path, dataset_root)
            js_output_path = os.path.join(output_base, "testfiles", relative_path.replace(".py", ".mjs"))
            if os.path.exists(js_output_path):
                print(f"Skipping (already exists): {relative_path}")
                continue
            os.makedirs(os.path.dirname(js_output_path), exist_ok=True)
            tasks.append((
                py_path, relative_path, dataset_root, output_base,
                model_name, api_base, provider, python_to_js_mapping, max_retries,
            ))
    return tasks


def main():
    dataset_root = str(REPO_ROOT / "Py2JS" / "dataset")
    max_retries = 2
    output_base = str(REPO_ROOT / "Py2JS" / "output_loop_mini" / f"{model_name}_retry{max_retries}")

    print("=" * 60)
    print("Python-to-JS migration using mini-swe-agent (loop mode)")
    print("=" * 60)
    print(f"Model:       {model_name}")
    print(f"API Base:    {api_base}")
    print(f"Provider:    {provider}")
    print(f"Processes:   {num_processes}")
    print(f"Max Retries: {max_retries}")
    print("=" * 60)

    tasks = collect_tasks(dataset_root, output_base, model_name, api_base, provider, python_to_js_mapping, max_retries)
    if not tasks:
        print("No tasks to process.")
        return

    print(f"\nStarting parallel processing ({num_processes} processes)...\n")

    success_count = 0
    failed_count = 0
    failed_tasks = []

    with Pool(processes=num_processes) as pool:
        results = pool.map(process_single_file, tasks)

    for result in results:
        if result["status"] == "success":
            success_count += 1
        else:
            failed_count += 1
            failed_tasks.append(result)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total:   {len(tasks)}")
    print(f"Success: {success_count}")
    print(f"Failed:  {failed_count}")
    print("=" * 60)

    if failed_tasks:
        print("\nFailed tasks:")
        for task in failed_tasks:
            err = task["error"] or ""
            print(f"  - {task['relative_path']}: {err[:100]}{'...' if len(err) > 100 else ''}")


if __name__ == "__main__":
    main()
