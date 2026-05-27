import json
import subprocess
import os
from collections import defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parent.parent
model_name = "ernie-5.0"

CPP_BASE = REPO_ROOT / "C2Rust" / "CppLarge"
RS_BASE = REPO_ROOT / "C2Rust" / "CppLarge" / "output_mini_large" / model_name / "packages"
CACHE_FILE = REPO_ROOT / "C2Rust" / "CppLarge" / "output_mini_large" / model_name / f"test_results_cache_{model_name}.json"
API_LINE_COUNTS = EVAL_ROOT / "testcases" / "c2rust" / "api_line_counts.jsonl"

gold_pkgs = [
    "Clipper",
    "sortedcontainers-cpp",
    "color",
    "indicators",
    "earcut.hpp",
    "immer",
    "hopscotch-map",
    "url-parser",
    "inflection-cpp",
    "exprtk",
    "idna-cpp",
]


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def compare_outputs(out1, out2):
    s1, s2 = out1.strip(), out2.strip()
    if s1 == s2:
        return True
    if is_float(s1) and is_float(s2):
        return float(s1) == float(s2)
    return False


def run_executable(path, args):
    if not os.path.exists(path):
        return None
    try:
        result = subprocess.run([path] + args, capture_output=True, text=True, timeout=3)
        return result.stdout
    except Exception:
        return None


def get_test_score(data):
    rel_path = data["file_name"]
    args = [str(v) for k, v in data.items() if k != "file_name"]

    cpp_exe_path = CPP_BASE / rel_path.replace(".cpp", "")
    if not os.access(cpp_exe_path, os.X_OK):
        return 0

    package_name = rel_path.split("/")[0]
    test_name = os.path.basename(rel_path).replace(".cpp", "")
    rs_search_dir = RS_BASE / package_name / f"{test_name}_pkg"

    rs_execs = []
    if rs_search_dir.exists():
        for root, _, files in os.walk(rs_search_dir):
            for file in files:
                if file == test_name:
                    p = os.path.join(root, file)
                    if os.access(p, os.X_OK):
                        rs_execs.append(p)

    if not rs_execs:
        return 0

    cpp_out = run_executable(str(cpp_exe_path), args)
    if cpp_out is None:
        return 0

    for rs_exe in rs_execs:
        rs_out = run_executable(rs_exe, args)
        if rs_out is not None and compare_outputs(cpp_out, rs_out):
            return 1
    return 0


def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)


def load_difficulty_groups(jsonl_path):
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append((obj["file"], obj["lib_total_lines"]))

    rows.sort(key=lambda item: item[1])
    total = len(rows)
    if total == 0:
        return {}

    base = total // 3
    remainder = total % 3
    sizes = [base + (1 if i < remainder else 0) for i in range(3)]
    buckets = ["easy", "medium", "hard"]

    groups = {}
    idx = 0
    for bucket, size in zip(buckets, sizes):
        for _ in range(size):
            if idx >= total:
                break
            groups[rows[idx][0]] = bucket
            idx += 1
    return groups


def main(input_jsonl):
    cache = load_cache()
    data_tree = defaultdict(lambda: defaultdict(list))
    new_runs = 0
    cached_runs = 0

    with open(input_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_data = json.loads(line)
            cache_key = json.dumps(raw_data, sort_keys=True)

            if cache_key in cache:
                score = cache[cache_key]
                cached_runs += 1
            else:
                score = get_test_score(raw_data)
                cache[cache_key] = score
                new_runs += 1

            if score is None:
                score = 0
            pkg_name = raw_data["file_name"].split("/")[0]
            data_tree[pkg_name][raw_data["file_name"]].append(score)

    save_cache(cache)
    print(f"\n[Summary] Loaded {cached_runs} from cache, ran {new_runs} new tests.")

    difficulty_groups = load_difficulty_groups(API_LINE_COUNTS)
    for key in difficulty_groups:
        num = int(key.split("/test")[-1].split(".")[0])
        if num < 7:
            difficulty_groups[key] = "easy"
        elif num < 14:
            difficulty_groups[key] = "medium"
        else:
            difficulty_groups[key] = "hard"

    bucket_stats = {
        "easy":   {"total_files": 0, "pass_files": 0, "sample_passes": 0, "sample_count": 0},
        "medium": {"total_files": 0, "pass_files": 0, "sample_passes": 0, "sample_count": 0},
        "hard":   {"total_files": 0, "pass_files": 0, "sample_passes": 0, "sample_count": 0},
    }

    pkg_stats = {}
    total_pass_files = 0
    total_all_files = 0
    all_samples = []

    for pkg, files in data_tree.items():
        if pkg not in gold_pkgs:
            continue
        file_all_pass = 0
        pkg_samples = []
        for fname, scores in files.items():
            is_all_pass = 1 if all(s == 1 for s in scores) else 0
            file_all_pass += is_all_pass
            pkg_samples.extend(scores)
            all_samples.extend(scores)

            bucket = difficulty_groups.get(fname)
            if bucket is not None:
                bucket_stats[bucket]["total_files"] += 1
                bucket_stats[bucket]["pass_files"] += is_all_pass
                bucket_stats[bucket]["sample_passes"] += sum(scores)
                bucket_stats[bucket]["sample_count"] += len(scores)

        pkg_total_files = len(files)
        pkg_stats[pkg] = {
            "total_files": pkg_total_files,
            "pass_files": file_all_pass,
            "all_pass_rate": file_all_pass / pkg_total_files if pkg_total_files else 0,
            "sample_rate": sum(pkg_samples) / len(pkg_samples) if pkg_samples else 0,
        }
        total_pass_files += file_all_pass
        total_all_files += pkg_total_files

    print("\n" + "=" * 70)
    print(f"{'Package':<15} | {'Files (Pass/Total)':<20} | {'File Pass%':<12} | {'Sample Pass%':<12}")
    print("-" * 70)
    for pkg, s in pkg_stats.items():
        file_ratio = f"{s['pass_files']}/{s['total_files']}"
        print(f"{pkg:<15} | {file_ratio:<20} | {s['all_pass_rate']:>10.2%} | {s['sample_rate']:>10.2%}")

    if not pkg_stats:
        print("\nNo valid test records found.")
        return

    macro_file_all_pass = sum(s["all_pass_rate"] for s in pkg_stats.values()) / len(pkg_stats)
    macro_sample_pass   = sum(s["sample_rate"]   for s in pkg_stats.values()) / len(pkg_stats)
    overall_file_all_pass = total_pass_files / total_all_files if total_all_files > 0 else 0
    overall_sample_pass   = sum(all_samples) / len(all_samples) if all_samples else 0

    for bucket, s in bucket_stats.items():
        s["all_pass_rate"]             = s["pass_files"]    / s["total_files"]  if s["total_files"]  else 0
        s["sample_pass_rate"]          = s["sample_passes"] / s["sample_count"] if s["sample_count"] else 0
        s["test_case_pass_rate"]       = s["sample_pass_rate"]
        s["total_test_case_pass_rate"] = s["sample_pass_rate"]

    print("\n" + "=" * 70)
    print("Difficulty Bucket Micro Stats (split by lib_total_lines into thirds)")
    print(f"{'Bucket':<8} | {'Files':<6} | {'File All-Pass%':<15} | {'Sample Pass%':<12} | {'Test Case%':<12} | {'Total Test Case%':<17}")
    print("-" * 70)
    for bucket in ("easy", "medium", "hard"):
        s = bucket_stats[bucket]
        print(f"{bucket:<8} | {s['total_files']:<6} | {s['all_pass_rate']:>13.2%} | {s['sample_pass_rate']:>10.2%} | {s['test_case_pass_rate']:>10.2%} | {s['total_test_case_pass_rate']:>15.2%}")

    print("\n" + "-" * 70)
    print("Summary Metrics")
    print("\n  File-level (all test cases in a file must pass)")
    print(f"  1. Micro All-Pass:  {overall_file_all_pass:>7.2%}  ({total_pass_files}/{total_all_files} files)")
    print(f"  2. Macro All-Pass:  {macro_file_all_pass:>7.2%}  (average across packages)")
    print("\n  Sample-level (each test case scored independently)")
    print(f"  3. Micro Sample:    {overall_sample_pass:>7.2%}  ({sum(all_samples)}/{len(all_samples)} samples)")
    print(f"  4. Macro Sample:    {macro_sample_pass:>7.2%}  (average across packages)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main(str(EVAL_ROOT / "testcases" / "c2rust" / "cleaned_test_cases.jsonl"))
