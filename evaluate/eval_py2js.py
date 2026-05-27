import argparse
import json
import subprocess
import os
from collections import defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent

REPO_ROOT = Path(__file__).resolve().parent.parent

PYTHON_BIN = os.environ.get("PYTHON_BIN", "python3")
NODE_BIN   = os.environ.get("NODE_BIN", "node")


def get_cleaned_lines(py_path, js_path, params):
    cmd_args = []
    for k, v in params.items():
        cmd_args.extend([f"--{k}", str(v)])

    try:
        py_proc = subprocess.run(
            [PYTHON_BIN, py_path] + cmd_args,
            capture_output=True, text=True, timeout=5,
        )
        js_proc = subprocess.run(
            [NODE_BIN, js_path] + cmd_args,
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None

    if py_proc.returncode == 0 and js_proc.returncode == 0:
        py_lines = ["".join(line.split()) for line in py_proc.stdout.strip().splitlines() if line.strip()]
        js_lines = ["".join(line.split()) for line in js_proc.stdout.strip().splitlines() if line.strip()]
        if len(py_lines) == len(js_lines) and len(py_lines) > 0:
            return py_lines, js_lines
    return None


def analyze_jsonl(jsonl_file, dataset_root, output_root, results_dir):
    data_groups = defaultdict(list)

    with open(jsonl_file, "r", encoding="utf-8") as f:
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
    file_pass_rates = {}

    for filename, samples in data_groups.items():
        py_path = os.path.join(dataset_root, filename)
        js_path = os.path.join(output_root, "testfiles", filename.replace(".py", ".mjs"))

        passed_samples = 0
        total_samples = len(samples)

        for params in samples:
            result = get_cleaned_lines(py_path, js_path, params)

            if result:
                py_lines, js_lines = result
                match_count = sum(
                    1 for i in range(len(py_lines))
                    if py_lines[i] == js_lines[i]
                )
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
            "total_samples": total_samples,
        }

        if passed_samples == total_samples:
            all_pass_files += 1

    all_pass_rate      = all_pass_files / file_count if file_count > 0 else 0
    test_case_pass_rate = sum(individual_pass_rates) / file_count if file_count > 0 else 0
    api_coverage = (
        sum(all_sample_api_rates) / len(all_sample_api_rates)
        if all_sample_api_rates else 0
    )

    os.makedirs(results_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(jsonl_file))[0]
    output_path = os.path.join(results_dir, f"{base_name}_file_pass_rates.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(file_pass_rates, f, indent=2, ensure_ascii=False)

    return {
        "all_pass_rate": all_pass_rate,
        "test_case_pass_rate": test_case_pass_rate,
        "api_coverage": api_coverage,
        "file_count": file_count,
        "all_pass_files": all_pass_files,
    }


def analyze_directory(jsonl_dir, dataset_root, output_root, results_dir):
    jsonl_files = sorted(f for f in os.listdir(jsonl_dir) if f.endswith(".jsonl"))
    print(f"Found {len(jsonl_files)} JSONL file(s)\n")

    results = []
    for file in jsonl_files:
        path = os.path.join(jsonl_dir, file)
        metrics = analyze_jsonl(path, dataset_root, output_root, results_dir)

        print(f"===== {file} =====")
        print(f"Files: {metrics['file_count']} total, {metrics['all_pass_files']} all-pass")
        print(f"All-pass Rate:       {metrics['all_pass_rate']:.4f}")
        print(f"Test Case Pass Rate: {metrics['test_case_pass_rate']:.4f}")
        print(f"API Coverage:        {metrics['api_coverage']:.4f}")
        print()
        results.append(metrics)

    def avg(key):
        return sum(r[key] for r in results) / len(results) if results else 0

    print("=" * 60)
    print("Overall Average:")
    print(f"All-pass Rate:       {avg('all_pass_rate'):.4f}")
    print(f"Test Case Pass Rate: {avg('test_case_pass_rate'):.4f}")
    print(f"API Coverage:        {avg('api_coverage'):.4f}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Python-to-JS migration results")
    parser.add_argument("-m", "--model", type=str, required=True, help="Model name")
    parser.add_argument(
        "--testcase-type",
        type=str,
        choices=["enhanced", "60"],
        default="enhanced",
        help="Testcase type: 'enhanced' for testcases_enhanced, '60' for testcases_60 (default: enhanced)",
    )
    parser.add_argument(
        "--jsonl-dir",
        type=str,
        default=None,
        help="Directory containing evaluation JSONL files (overrides --testcase-type if specified)",
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=str(REPO_ROOT / "Py2JS" / "dataset"),
        help="Root directory of the Python dataset",
    )
    args = parser.parse_args()

    # Determine jsonl_dir based on testcase_type or explicit --jsonl-dir
    if args.jsonl_dir is not None:
        jsonl_dir = args.jsonl_dir
    elif args.testcase_type == "enhanced":
        jsonl_dir = str(EVAL_ROOT / "testcases" / "testcases_enhanced")
    else:  # "60"
        jsonl_dir = str(EVAL_ROOT / "testcases" / "testcases_60")

    model_name   = args.model
    output_root  = str(REPO_ROOT / "Py2JS" / "output" / model_name)
    results_dir  = str(EVAL_ROOT / "results" / model_name)

    analyze_directory(jsonl_dir, args.dataset_root, output_root, results_dir)


if __name__ == "__main__":
    main()
