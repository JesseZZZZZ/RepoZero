import json
import subprocess
import os
import argparse
from collections import defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parent.parent

# Default test files to evaluate
DEFAULT_VALID_IDS = [
    'boltons/test10.py', 'fractions/test14.py', 'deepdiff/test16.py', 'bech32/test4.py', 'idna/test13.py', 'base58/test6.py', 'bech32/test12.py', 'canonicaljson/test20.py', 'idna/test6.py', 'jsonschema/test7.py', 'schedule/test9.py', 'bidict/test5.py', 'mpmath/test4.py', 'furl/test5.py', 'furl/test11.py', 'bidict/test13.py', 'bech32/test2.py', 'networkx/test14.py', 'yaml/test16.py', 'bech32/test9.py', 'idna/test9.py', 'base58/test1.py', 'networkx/test5.py', 'moneyed/test6.py', 'bencoder/test7.py', 'pyaes/test10.py', 'markdown/test13.py', 'networkx/test4.py', 'bencoder/test15.py', 'jsonschema/test15.py', 'networkx/test16.py', 'markdown/test19.py', 'base58/test2.py', 'rsa/test15.py', 'construct/test12.py', 'rsa/test19.py', 'whoosh/test2.py', 'moneyed/test17.py', 'networkx/test13.py', 'networkx/test7.py', 'mpmath/test12.py', 'rsa/test8.py', 'canonicaljson/test14.py', 'networkx/test3.py', 'base58/test7.py', 'boltons/test14.py', 'boltons/test3.py', 'idna/test4.py', 'boltons/test11.py', 'mpmath/test1.py', 'base58/test19.py', 'moneyed/test3.py', 'bech32/test13.py', 'construct/test16.py', 'pyaes/test17.py', 'sqlparse/test4.py', 'jose/test7.py', 'idna/test18.py', 'jose/test13.py', 'whoosh/test7.py', 'bidict/test10.py', 'pyaes/test2.py', 'whoosh/test6.py', 'yaml/test2.py', 'deepdiff/test3.py', 'canonicaljson/test8.py', 'whoosh/test1.py', 'bencoder/test6.py', 'bidict/test17.py', 'moneyed/test15.py', 'pyaes/test12.py', 'idna/test11.py', 'deepdiff/test18.py', 'sqlparse/test2.py', 'rsa/test5.py', 'yaml/test11.py', 'canonicaljson/test11.py', 'schedule/test13.py', 'schedule/test2.py', 'jsonschema/test8.py', 'mpmath/test19.py', 'pyaes/test9.py', 'pyaes/test19.py', 'fractions/test15.py', 'markdown/test11.py', 'bidict/test16.py', 'construct/test20.py', 'yaml/test6.py', 'mpmath/test13.py', 'mpmath/test18.py', 'idna/test12.py', 'bech32/test15.py', 'yaml/test12.py', 'boltons/test15.py', 'deepdiff/test10.py', 'rsa/test16.py', 'boltons/test4.py', 'furl/test12.py', 'moneyed/test12.py', 'whoosh/test20.py', 'schedule/test19.py', 'bidict/test3.py', 'base58/test17.py', 'fractions/test2.py', 'moneyed/test7.py', 'whoosh/test3.py', 'mpmath/test7.py', 'construct/test17.py', 'idna/test15.py', 'mpmath/test17.py', 'markdown/test4.py', 'mpmath/test11.py', 'bech32/test1.py', 'bidict/test12.py', 'bencoder/test5.py', 'mpmath/test16.py', 'jose/test15.py', 'pyaes/test4.py', 'canonicaljson/test1.py', 'bech32/test14.py', 'moneyed/test14.py', 'jsonschema/test9.py', 'fractions/test19.py', 'construct/test19.py', 'yaml/test10.py', 'canonicaljson/test17.py', 'markdown/test7.py', 'schedule/test10.py', 'jsonschema/test10.py', 'mpmath/test15.py', 'bencoder/test8.py', 'bidict/test8.py', 'canonicaljson/test9.py', 'bencoder/test18.py', 'base58/test15.py', 'moneyed/test9.py', 'boltons/test6.py', 'boltons/test5.py', 'fractions/test6.py', 'jose/test9.py', 'yaml/test5.py', 'moneyed/test11.py', 'yaml/test7.py', 'bidict/test14.py', 'fractions/test5.py', 'boltons/test17.py', 'jsonschema/test20.py', 'deepdiff/test4.py', 'construct/test15.py', 'construct/test7.py', 'idna/test17.py', 'networkx/test6.py', 'whoosh/test18.py', 'jsonschema/test14.py', 'fractions/test4.py', 'jose/test10.py', 'rsa/test7.py', 'canonicaljson/test13.py', 'furl/test6.py', 'canonicaljson/test5.py', 'boltons/test7.py', 'yaml/test15.py', 'base58/test13.py', 'bencoder/test3.py', 'pyaes/test11.py', 'pbkdf2/test16.py', 'bech32/test3.py', 'jose/test12.py', 'moneyed/test19.py', 'deepdiff/test1.py', 'boltons/test9.py', 'markdown/test14.py', 'pyaes/test8.py', 'bencoder/test17.py', 'fractions/test1.py', 'schedule/test3.py', 'jose/test1.py', 'idna/test16.py', 'bech32/test11.py', 'jose/test6.py', 'base58/test9.py', 'mpmath/test3.py', 'bencoder/test13.py', 'bidict/test11.py', 'idna/test8.py', 'schedule/test6.py', 'bidict/test7.py', 'pbkdf2/test15.py', 'moneyed/test2.py', 'pbkdf2/test11.py', 'rsa/test11.py', 'jsonschema/test18.py', 'jsonschema/test6.py', 'base58/test12.py', 'yaml/test18.py', 'bencoder/test2.py', 'construct/test5.py', 'furl/test10.py', 'boltons/test1.py', 'deepdiff/test11.py', 'bech32/test8.py', 'furl/test9.py', 'fractions/test16.py', 'whoosh/test9.py', 'schedule/test18.py', 'bech32/test16.py', 'base58/test16.py', 'whoosh/test15.py', 'jsonschema/test2.py', 'schedule/test14.py', 'moneyed/test13.py', 'yaml/test9.py', 'jose/test19.py', 'bidict/test6.py', 'markdown/test12.py', 'base58/test14.py', 'whoosh/test4.py', 'bidict/test1.py', 'pyaes/test13.py', 'idna/test19.py', 'networkx/test15.py', 'idna/test2.py', 'pyaes/test7.py', 'bidict/test18.py', 'whoosh/test17.py', 'bencoder/test10.py', 'yaml/test20.py', 'bidict/test20.py', 'pyaes/test14.py', 'bencoder/test9.py', 'whoosh/test11.py', 'base58/test20.py', 'markdown/test16.py', 'furl/test3.py', 'furl/test2.py', 'yaml/test1.py', 'moneyed/test18.py', 'moneyed/test5.py', 'sqlparse/test9.py', 'whoosh/test14.py', 'schedule/test20.py', 'base58/test8.py', 'sqlparse/test16.py', 'idna/test7.py', 'idna/test20.py', 'pbkdf2/test13.py', 'furl/test4.py', 'construct/test18.py', 'jsonschema/test5.py', 'schedule/test12.py', 'bidict/test19.py', 'furl/test7.py', 'construct/test3.py', 'deepdiff/test15.py', 'markdown/test1.py', 'schedule/test4.py', 'jsonschema/test1.py', 'construct/test10.py', 'schedule/test16.py', 'construct/test14.py', 'bencoder/test11.py', 'schedule/test5.py', 'boltons/test19.py', 'bencoder/test14.py', 'jsonschema/test13.py', 'fractions/test13.py', 'schedule/test1.py', 'base58/test4.py', 'jose/test17.py', 'jsonschema/test19.py', 'bech32/test7.py', 'mpmath/test5.py', 'canonicaljson/test18.py', 'jose/test3.py', 'furl/test13.py', 'base58/test18.py', 'fractions/test20.py', 'jsonschema/test4.py', 'markdown/test15.py', 'markdown/test9.py', 'sqlparse/test3.py', 'boltons/test13.py', 'markdown/test6.py', 'markdown/test3.py', 'rsa/test18.py', 'fractions/test3.py', 'pyaes/test15.py', 'bencoder/test16.py', 'boltons/test2.py', 'fractions/test17.py', 'jose/test2.py', 'canonicaljson/test3.py', 'canonicaljson/test7.py', 'networkx/test2.py', 'pbkdf2/test7.py', 'yaml/test14.py', 'mpmath/test6.py', 'pyaes/test18.py', 'whoosh/test19.py', 'jsonschema/test12.py', 'moneyed/test1.py', 'pbkdf2/test14.py', 'whoosh/test16.py', 'deepdiff/test2.py', 'bencoder/test1.py', 'networkx/test17.py', 'construct/test1.py', 'pyaes/test16.py', 'markdown/test8.py', 'markdown/test17.py', 'canonicaljson/test15.py', 'construct/test6.py', 'jose/test4.py', 'pbkdf2/test8.py', 'bencoder/test12.py', 'rsa/test2.py', 'networkx/test20.py', 'canonicaljson/test16.py', 'construct/test8.py', 'pyaes/test5.py', 'yaml/test8.py', 'sqlparse/test10.py', 'idna/test3.py', 'schedule/test11.py', 'canonicaljson/test10.py', 'markdown/test2.py', 'mpmath/test9.py', 'bidict/test15.py', 'markdown/test5.py', 'canonicaljson/test2.py', 'boltons/test12.py', 'whoosh/test8.py', 'moneyed/test10.py', 'jsonschema/test11.py', 'canonicaljson/test19.py', 'pyaes/test6.py', 'pbkdf2/test1.py', 'pbkdf2/test4.py', 'sqlparse/test7.py', 'bidict/test4.py', 'furl/test1.py', 'markdown/test10.py', 'yaml/test17.py', 'base58/test11.py', 'jose/test8.py', 'rsa/test17.py', 'yaml/test4.py', 'idna/test10.py', 'furl/test8.py', 'construct/test4.py', 'jsonschema/test16.py', 'fractions/test12.py', 'bech32/test10.py', 'canonicaljson/test4.py', 'rsa/test10.py', 'bencoder/test4.py', 'bidict/test9.py', 'construct/test2.py', 'yaml/test19.py', 'pbkdf2/test2.py', 'fractions/test7.py', 'pbkdf2/test10.py', 'whoosh/test10.py', 'mpmath/test14.py', 'bidict/test2.py', 'idna/test1.py', 'networkx/test1.py', 'mpmath/test8.py', 'idna/test14.py', 'jsonschema/test3.py', 'base58/test10.py', 'deepdiff/test6.py', 'idna/test5.py', 'deepdiff/test12.py', 'moneyed/test8.py', 'canonicaljson/test6.py', 'fractions/test8.py', 'jose/test16.py', 'fractions/test9.py', 'mpmath/test10.py', 'networkx/test11.py', 'fractions/test11.py', 'markdown/test20.py', 'markdown/test18.py', 'bencoder/test19.py', 'base58/test3.py', 'yaml/test13.py', 'jose/test11.py', 'pbkdf2/test6.py', 'canonicaljson/test12.py', 'networkx/test10.py', 'schedule/test7.py', 'bech32/test17.py', 'moneyed/test20.py', 'bech32/test6.py', 'mpmath/test2.py', 'whoosh/test5.py', 'bech32/test5.py', 'moneyed/test16.py', 'base58/test5.py'
]


def get_entry_point_from_package(pkg_dir):
    """Read entry point file location from package directory"""
    # Find the main .mjs file (typically named after the test)
    mjs_files = [f for f in os.listdir(pkg_dir) if f.endswith('.mjs')]
    if mjs_files:
        # Prefer the main test file (e.g., test1.mjs)
        for f in mjs_files:
            if f.startswith('test') and f != 'package.json':
                return os.path.join(pkg_dir, f)
        # Fallback to first mjs file
        return os.path.join(pkg_dir, mjs_files[0])
    return None


def get_cleaned_lines(py_path, js_entry_path, params, python_bin, node_bin):
    """
    Execute both Python and JavaScript with given parameters and compare output.

    Args:
        py_path: Path to Python test file
        js_entry_path: Path to JavaScript entry point (.mjs)
        params: Dictionary of parameters
        python_bin: Python interpreter path
        node_bin: Node.js interpreter path

    Returns:
        Tuple of (py_lines, js_lines) if both succeed, None otherwise
    """
    cmd_args = []
    for k, v in params.items():
        cmd_args.extend([f"--{k}", str(v)])

    try:
        # Get Python executable path (test1.py -> test1_executable)
        py_dir = os.path.dirname(py_path)
        py_name = os.path.basename(py_path)
        py_executable = os.path.join(py_dir, py_name.replace('.py', '_executable'))

        # Execute Python executable file
        py_proc = subprocess.run(
            [py_executable] + cmd_args,
            capture_output=True,
            text=True,
            timeout=5
        )
        # Execute JavaScript file
        js_proc = subprocess.run(
            [node_bin, js_entry_path] + cmd_args,
            capture_output=True,
            text=True,
            timeout=5
        )
    except Exception:
        return None

    if py_proc.returncode == 0 and js_proc.returncode == 0:
        # Clean output lines (remove extra whitespace)
        py_lines = ["".join(line.split()) for line in py_proc.stdout.strip().splitlines() if line.strip()]
        js_lines = ["".join(line.split()) for line in js_proc.stdout.strip().splitlines() if line.strip()]

        if len(py_lines) == len(js_lines) and len(py_lines) > 0:
            return py_lines, js_lines
    return None


def analyze_jsonl(jsonl_file, model_name, dataset_root, output_root, python_bin, node_bin):
    """
    Analyze a single JSONL test case file and compute pass rates.

    Args:
        jsonl_file: Path to JSONL test case file
        model_name: Name of the model being evaluated
        dataset_root: Root directory of the source dataset
        output_root: Root directory of generated outputs
        python_bin: Path to Python interpreter
        node_bin: Path to Node.js interpreter

    Returns:
        Dictionary containing evaluation metrics
    """
    # First check if complete results already exist
    output_dir = os.path.join(output_root, "results", f"{model_name}_docker")
    results_dir = str(EVAL_ROOT / "results" / model_name)
    base_name = os.path.splitext(os.path.basename(jsonl_file))[0]
    output_path = os.path.join(output_dir, f"{base_name}_file_pass_rates.json")

    # Check if results file exists and contains all valid_ids tests
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_results = json.load(f)
        # Check if tested files count equals valid_ids length
        tested_files = set(existing_results.keys())
        expected_files = set(DEFAULT_VALID_IDS)
        if len(tested_files) == len(expected_files) and tested_files == expected_files:
            print(f"[SKIP] {base_name} - Complete test results already exist ({len(tested_files)} files)")
            # Calculate metrics
            all_pass_files = sum(1 for r in existing_results.values() if r['pass_rate'] == 1.0)
            file_count = len(existing_results)
            test_case_pass_rate = sum(r['pass_rate'] for r in existing_results.values()) / file_count
            # API coverage cannot be recalculated from cache, return N/A for now
            return {
                "all_pass_rate": all_pass_files / file_count,
                "test_case_pass_rate": test_case_pass_rate,
                "api_coverage": 0.0,  # Cannot calculate from cache
                "file_count": file_count,
                "all_pass_files": all_pass_files,
                "cached": True  # Mark as cached result
            }
        else:
            print(f"[CONTINUE] Results file exists but incomplete (tested {len(tested_files)}/{len(expected_files)} files), continuing...")

    data_groups = defaultdict(list)

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            fname = item.pop("filename")
            data_groups[fname].append(item)

    file_count = len(data_groups)
    all_pass_files = 0
    individual_pass_rates = []
    all_sample_api_rates = []
    # Store pass rate for each file
    file_pass_rates = {}

    for filename, samples in data_groups.items():
        # Parse filename, e.g., "bencoder/test1.py" -> "bencoder" and "test1"
        if not filename in DEFAULT_VALID_IDS:
            continue
        parts = filename.replace(".py", "").split("/")
        if len(parts) != 2:
            continue
        pkg_name, test_name = parts

        py_path = os.path.join(dataset_root, filename)

        # Build package directory path: packages/bencoder/test1_pkg/
        pkg_dir = None
        for base_dir in [
            os.path.join(output_root, "packages"),
        ]:
            test_pkg_dir = os.path.join(base_dir, pkg_name, f"{test_name}_pkg")
            print(test_pkg_dir)
            if os.path.exists(test_pkg_dir):
                pkg_dir = test_pkg_dir
                break

        # Get entry point from package directory
        js_entry_path = None
        if pkg_dir:
            js_entry_path = get_entry_point_from_package(pkg_dir)

        passed_samples = 0
        total_samples = len(samples)

        for params in samples:
            if js_entry_path:
                result = get_cleaned_lines(py_path, js_entry_path, params, python_bin, node_bin)
            else:
                result = None

            if result:
                py_lines, js_lines = result
                match_count = sum(
                    1 for i in range(len(py_lines))
                    if py_lines[i] == js_lines[i]
                )

                # API coverage (within sample)
                sample_api_rate = match_count / len(py_lines)
                all_sample_api_rates.append(sample_api_rate)

                if match_count == len(py_lines):
                    passed_samples += 1
            else:
                all_sample_api_rates.append(0.0)

        current_rate = passed_samples / total_samples if total_samples > 0 else 0
        individual_pass_rates.append(current_rate)
        file_pass_rates[filename] = {
            "pass_rate": current_rate,
            "passed_samples": passed_samples,
            "total_samples": total_samples
        }

        if passed_samples == total_samples:
            all_pass_files += 1

    # ===== Three metrics =====
    all_pass_rate = all_pass_files / file_count if file_count > 0 else 0
    test_case_pass_rate = sum(individual_pass_rates) / file_count if file_count > 0 else 0
    api_coverage = (
        sum(all_sample_api_rates) / len(all_sample_api_rates)
        if all_sample_api_rates else 0
    )

    # Save per-file pass rates to JSON file
    os.makedirs(results_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(jsonl_file))[0]
    output_path = os.path.join(results_dir, f"{base_name}_file_pass_rates.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(file_pass_rates, f, indent=2, ensure_ascii=False)

    return {
        "all_pass_rate": all_pass_rate,
        "test_case_pass_rate": test_case_pass_rate,
        "api_coverage": api_coverage,
        "file_count": file_count,
        "all_pass_files": all_pass_files
    }


def analyze_directory(jsonl_dir, model_name, dataset_root, output_root, python_bin, node_bin):
    """
    Analyze all JSONL files in a directory and compute average metrics.

    Args:
        jsonl_dir: Directory containing JSONL test case files
        model_name: Name of the model being evaluated
        dataset_root: Root directory of the source dataset
        output_root: Root directory of generated outputs
        python_bin: Path to Python interpreter
        node_bin: Path to Node.js interpreter
    """
    results = []

    jsonl_files = [f for f in os.listdir(jsonl_dir) if f.endswith(".jsonl")]

    print(f"[INFO] Found {len(jsonl_files)} JSONL files\n")

    for file in jsonl_files:
        path = os.path.join(jsonl_dir, file)
        metrics = analyze_jsonl(path, model_name, dataset_root, output_root, python_bin, node_bin)

        print(f"===== {file} =====")
        if metrics.get('cached'):
            print("[FROM CACHE]")
        print(f"Total test files: {metrics['file_count']}, all-pass files: {metrics['all_pass_files']}")
        print(f"All-pass Rate: {metrics['all_pass_rate']:.4f}")
        print(f"Test Case Pass Rate: {metrics['test_case_pass_rate']:.4f}")
        if not metrics.get('cached'):
            print(f"API Coverage: {metrics['api_coverage']:.4f}")
        print()

        results.append(metrics)

    def avg(key):
        return sum(r[key] for r in results) / len(results) if results else 0

    print("=" * 60)
    print("Overall Average Results:")
    print(f"All-pass Rate: {avg('all_pass_rate'):.4f}")
    print(f"Test Case Pass Rate: {avg('test_case_pass_rate'):.4f}")
    print(f"API Coverage: {avg('api_coverage'):.4f}")


def main():
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate Py2JS translation results (Docker-based output)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate with default settings
  python eval_py2js_docker.py

  # Evaluate specific model
  python eval_py2js_docker.py -m deepseek-v3.2

  # Specify custom paths
  python eval_py2js_docker.py --dataset-root ./Py2JS/dataset \\
      --output-root ./Py2JS/output \\
      --jsonl-dir ./Py2JS/testcases_60
        """
    )
    parser.add_argument(
        "-m", "--model-name",
        type=str,
        default="deepseek-v3.2",
        help="Model name to evaluate (default: deepseek-v3.2)"
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="Root directory of the source dataset (default: ./Py2JS/dataset)"
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Root directory of generated outputs (default: ./Py2JS/output)"
    )
    parser.add_argument(
        "--jsonl-dir",
        type=str,
        default=None,
        help="Directory containing JSONL test case files (default: ./Py2JS/testcases_60)"
    )
    parser.add_argument(
        "--python-bin",
        type=str,
        default="python3",
        help="Python interpreter path (default: python3)"
    )
    parser.add_argument(
        "--node-bin",
        type=str,
        default="node",
        help="Node.js interpreter path (default: node)"
    )

    args = parser.parse_args()

    # Set default paths relative to script location
    script_dir = EVAL_ROOT
    repo_root = script_dir.parent

    dataset_root = args.dataset_root
    if dataset_root is None:
        dataset_root = str(repo_root / "Py2JS" / "dataset")

    output_root = args.output_root
    if output_root is None:
        output_root = str(repo_root / "Py2JS" / "output")

    jsonl_dir = args.jsonl_dir
    if jsonl_dir is None:
        jsonl_dir = str(EVAL_ROOT / "testcases" / "py2js")

    print(f"[CONFIG] Model: {args.model_name}")
    print(f"[CONFIG] Dataset root: {dataset_root}")
    print(f"[CONFIG] Output root: {output_root}")
    print(f"[CONFIG] Test cases dir: {jsonl_dir}")
    print(f"[CONFIG] Python: {args.python_bin}, Node: {args.node_bin}")
    print()

    analyze_directory(jsonl_dir, args.model_name, dataset_root, output_root, args.python_bin, args.node_bin)


if __name__ == "__main__":
    main()
