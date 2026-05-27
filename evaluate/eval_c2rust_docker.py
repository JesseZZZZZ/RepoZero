import json
import subprocess
import os
import argparse
import uuid
from collections import defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parent.parent

# Docker image for C2Rust evaluation
DOCKER_IMAGE = "ghcr.io/jessezzzzz/c2rust-arena:latest"

# Container workspace
CONTAINER_WORKSPACE = "/workspace"

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

ERR_NO_EXEC      = "no_executable"
ERR_FIRST4_FAIL  = "first4_not_pass"
ERR_RUNTIME      = "runtime_error"
ERR_WRONG_OUTPUT = "wrong_output"
ERR_ALL_PASS     = "all_pass"


# ===== Docker Helper Functions =====

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


def ensure_image_exists(image_name):
    """Ensure Docker image exists, pull from registry if not"""
    success, stdout, stderr = run_docker_command(f"docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}}' | grep '^{image_name}$'", timeout=10)
    if success and image_name in stdout:
        print(f"[OK] Docker image {image_name} already exists locally")
        return True

    print(f"[PULL] Image {image_name} not found locally, pulling from registry...")
    success, stdout, stderr = run_docker_command(f"docker pull {image_name}", timeout=300)
    if success:
        print(f"[OK] Docker image {image_name} pulled successfully")
        return True
    else:
        print(f"[ERROR] Failed to pull Docker image {image_name}: {stderr}")
        return False


def create_temp_container(image_name):
    """Create a temporary container for evaluation"""
    container_name = f"eval-c2rust-{uuid.uuid4().hex[:8]}"

    if not ensure_image_exists(image_name):
        return None

    docker_cmd = f"docker run -d --name {container_name} "
    docker_cmd += f"--network none "
    docker_cmd += f"-w {CONTAINER_WORKSPACE} "
    docker_cmd += f"{image_name} tail -f /dev/null"

    success, stdout, stderr = run_docker_command(docker_cmd, timeout=30)

    if not success:
        print(f"[ERROR] Failed to start container: {stderr}")
        return None

    print(f"[OK] Created container: {container_name}")
    return container_name


def cleanup_container(container_name):
    """Remove a container"""
    if container_name:
        run_docker_command(f"docker rm -f {container_name}", timeout=10)


def docker_exec_file(host_path, container_name, container_path, args, timeout=3):
    """
    Copy a file to container and execute it.

    Args:
        host_path: Path to file on host
        container_name: Docker container name
        container_path: Path where file will be placed in container
        args: Command line arguments (list)
        timeout: Execution timeout

    Returns:
        Tuple of (stdout, had_error) or (None, True) on failure
    """
    if not os.path.exists(host_path):
        return None, True

    copy_cmd = ["docker", "cp", host_path, f"{container_name}:{container_path}"]
    try:
        result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None, True
    except Exception:
        return None, True

    run_docker_command(f"docker exec {container_name} chmod +x {container_path}", timeout=5)

    exec_cmd = f"docker exec {container_name} {container_path} " + " ".join(args)

    try:
        result = subprocess.run(
            exec_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.returncode != 0
    except subprocess.TimeoutExpired:
        return None, True
    except Exception:
        return None, True


# ===== Evaluation Functions =====

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


def run_executable_in_docker(host_path, container_name, args, timeout=3):
    """Run a binary in Docker container and return (stdout, had_error)."""
    container_path = f"{CONTAINER_WORKSPACE}/exec"
    return docker_exec_file(host_path, container_name, container_path, args, timeout)

count = 0
def get_test_score(data, cpp_base, rs_base, container_name):
    global count
    count += 1
    
    rel_path = data["file_name"]
    print(f"[{count}] {rel_path}")
    args = [str(v) for k, v in data.items() if k != "file_name"]

    cpp_exe_path = os.path.join(cpp_base, rel_path.replace(".cpp", ""))
    if not os.path.exists(cpp_exe_path):
        return 0

    package_name = rel_path.split("/")[0]
    test_name = os.path.basename(rel_path).replace(".cpp", "")
    rs_search_dir = os.path.join(rs_base, package_name, f"{test_name}_pkg")

    rs_execs = []
    if os.path.exists(rs_search_dir):
        for root, _, files in os.walk(rs_search_dir):
            for file in files:
                if file == test_name:
                    p = os.path.join(root, file)
                    if os.access(p, os.X_OK):
                        rs_execs.append(p)

    if not rs_execs:
        return 0

    cpp_out, _ = run_executable_in_docker(str(cpp_exe_path), container_name, args)
    if cpp_out is None:
        return 0

    for rs_exe in rs_execs:
        rs_out, _ = run_executable_in_docker(rs_exe, container_name, args)
        if rs_out is not None and compare_outputs(cpp_out, rs_out):
            return 1
    return 0


def load_cache(cache_file):
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache, cache_file):
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
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


def classify_file_error(fname, scores_with_meta):
    """Classify the error category for a single test file based on its case results."""
    if not scores_with_meta:
        return ERR_NO_EXEC

    scores = [s for s, _ in scores_with_meta]
    errors = [e for _, e in scores_with_meta]

    if all(s == 1 for s in scores):
        return ERR_ALL_PASS

    if not all(s == 1 for s in scores[:4]):
        return ERR_FIRST4_FAIL

    if any(errors):
        return ERR_RUNTIME

    return ERR_WRONG_OUTPUT


def classify_all_files(rs_base, cpp_base, input_jsonl, gold_pkgs_set, container_name):
    """Classify every file in gold_pkgs by error category, preserving case order."""
    file_cases = defaultdict(list)
    with open(input_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_data = json.loads(line)
            fname = raw_data["file_name"]
            pkg = fname.split("/")[0]
            if pkg in gold_pkgs_set:
                file_cases[fname].append(raw_data)

    result = {}
    for fname, cases in file_cases.items():
        package_name = fname.split("/")[0]
        test_name = os.path.basename(fname).replace(".cpp", "")
        rs_search_dir = os.path.join(rs_base, package_name, f"{test_name}_pkg")

        rs_execs = []
        if os.path.exists(rs_search_dir):
            for root, _, files in os.walk(rs_search_dir):
                for file in files:
                    if file == test_name:
                        p = os.path.join(root, file)
                        if os.access(p, os.X_OK):
                            rs_execs.append(p)

        if not rs_execs:
            result[fname] = ERR_NO_EXEC
            continue

        cpp_exe_path = os.path.join(cpp_base, fname.replace(".cpp", ""))
        if not os.path.exists(cpp_exe_path):
            result[fname] = ERR_NO_EXEC
            continue

        scores_with_meta = []
        for raw_data in cases:
            args = [str(v) for k, v in raw_data.items() if k != "file_name"]
            cpp_out, _ = run_executable_in_docker(cpp_exe_path, container_name, args)
            if cpp_out is None:
                continue

            case_score = 0
            case_had_error = False
            for rs_exe in rs_execs:
                rs_out, had_error = run_executable_in_docker(rs_exe, container_name, args)
                if had_error:
                    case_had_error = True
                if rs_out is not None and compare_outputs(cpp_out, rs_out):
                    case_score = 1
                    case_had_error = False
                    break
            scores_with_meta.append((case_score, case_had_error))

        result[fname] = classify_file_error(fname, scores_with_meta)

    return result


def main(input_jsonl, model_name, cpp_base, rs_base, cache_file, api_line_counts, docker_image):
    cache = load_cache(cache_file)
    data_tree = defaultdict(lambda: defaultdict(list))
    new_runs = 0
    cached_runs = 0

    # Create container for all executions
    container_name = create_temp_container(docker_image)
    if not container_name:
        print("[ERROR] Failed to create Docker container")
        return

    try:
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
                    score = get_test_score(raw_data, cpp_base, rs_base, container_name)
                    cache[cache_key] = score
                    new_runs += 1

                if score is not None:
                    pkg_name = raw_data["file_name"].split("/")[0]
                    data_tree[pkg_name][raw_data["file_name"]].append(score)

        save_cache(cache, cache_file)
        print(f"\n[Summary] Loaded {cached_runs} from cache, ran {new_runs} new tests.")

        difficulty_groups = load_difficulty_groups(api_line_counts)
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
            s["all_pass_rate"]            = s["pass_files"]    / s["total_files"]  if s["total_files"]  else 0
            s["sample_pass_rate"]         = s["sample_passes"] / s["sample_count"] if s["sample_count"] else 0
            s["test_case_pass_rate"]      = s["sample_pass_rate"]
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

        print("\n" + "=" * 70)
        print("Rust Error Classification (per file)")
        print("Re-running all files to collect detailed error info...")

        gold_set = set(gold_pkgs)
        file_error_map = classify_all_files(rs_base, cpp_base, input_jsonl, gold_set, container_name)

        error_counts = {
            ERR_NO_EXEC:      0,
            ERR_FIRST4_FAIL:  0,
            ERR_RUNTIME:      0,
            ERR_WRONG_OUTPUT: 0,
            ERR_ALL_PASS:     0,
        }
        error_files = defaultdict(list)

        for fname, err in file_error_map.items():
            error_counts[err] += 1
            error_files[err].append(fname)

        total_classified = sum(error_counts.values())

        label_map = {
            ERR_NO_EXEC:      "1. No executable generated",
            ERR_FIRST4_FAIL:  "2. First 4 cases not all passing",
            ERR_RUNTIME:      "3. Runtime error / timeout",
            ERR_WRONG_OUTPUT: "4. Output differs from C++",
            ERR_ALL_PASS:     "   All pass",
        }

        print(f"\n{'Category':<35} | {'Files':>6} | {'Ratio':>8}")
        print("-" * 55)
        for key in [ERR_ALL_PASS, ERR_NO_EXEC, ERR_FIRST4_FAIL, ERR_RUNTIME, ERR_WRONG_OUTPUT]:
            cnt = error_counts[key]
            pct = cnt / total_classified if total_classified else 0
            print(f"{label_map[key]:<35} | {cnt:>6} | {pct:>7.2%}")
        print("-" * 55)
        print(f"{'Total':<35} | {total_classified:>6}")

        print("\n\n--- Per-Package Breakdown ---")
        pkg_error_counts = defaultdict(lambda: defaultdict(int))
        for fname, err in file_error_map.items():
            pkg = fname.split("/")[0]
            pkg_error_counts[pkg][err] += 1

        col_keys  = [ERR_ALL_PASS, ERR_NO_EXEC, ERR_FIRST4_FAIL, ERR_RUNTIME, ERR_WRONG_OUTPUT]
        col_short = ["All Pass", "No Exec", "First4 Fail", "Runtime Err", "Wrong Out"]
        header = f"{'Package':<20}" + "".join(f" | {h:>11}" for h in col_short)
        print(header)
        print("-" * (20 + 14 * len(col_keys)))
        for pkg in sorted(pkg_error_counts.keys()):
            row = f"{pkg:<20}"
            for key in col_keys:
                row += f" | {pkg_error_counts[pkg][key]:>11}"
            print(row)

        print("=" * 70 + "\n")

    finally:
        cleanup_container(container_name)
        print(f"\n[CLEANUP] Removed container: {container_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate C2Rust translation results (Docker-based)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate with default settings
  python eval_c2rust_docker.py

  # Evaluate specific model
  python eval_c2rust_docker.py -m deepseek-v3.1-250821

  # Specify custom paths
  python eval_c2rust_docker.py --cpp-base ./C2Rust/CppLarge \\
      --rs-base ./output/C2Rust/deepseek-v3.1-250821/packages \\
      --api-line-counts ./evaluate/testcases/c2rust/api_line_counts.jsonl
        """
    )
    parser.add_argument(
        "-m", "--model-name",
        type=str,
        default="deepseek-v3.1-250821",
        help="Model name to evaluate (default: deepseek-v3.1-250821)"
    )
    parser.add_argument(
        "--cpp-base",
        type=str,
        default=None,
        help="C++ base directory (default: ./C2Rust/CppLarge)"
    )
    parser.add_argument(
        "--rs-base",
        type=str,
        default=None,
        help="Rust output directory (default: ./output/C2Rust/{model_name}/packages)"
    )
    parser.add_argument(
        "--input-jsonl",
        type=str,
        default=None,
        help="Input JSONL test cases file (default: ./evaluate/testcases/c2rust/cleaned_test_cases.jsonl)"
    )
    parser.add_argument(
        "--api-line-counts",
        type=str,
        default=None,
        help="API line counts JSONL file (default: ./evaluate/testcases/c2rust/api_lines.jsonl)"
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None,
        help="Cache file path (default: ./output/C2Rust/{model_name}/test_results_cache_{model_name}.json)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3,
        help="Execution timeout in seconds (default: 3)"
    )
    parser.add_argument(
        "--docker-image",
        type=str,
        default=DOCKER_IMAGE,
        help=f"Docker image to use (default: {DOCKER_IMAGE})"
    )

    args = parser.parse_args()

    script_dir = EVAL_ROOT
    repo_root = script_dir.parent

    cpp_base = args.cpp_base
    if cpp_base is None:
        cpp_base = str(repo_root / "C2Rust" / "CppLarge")

    rs_base = args.rs_base
    if rs_base is None:
        rs_base = str(repo_root / "output" / "C2Rust" / args.model_name / "packages")

    input_jsonl = args.input_jsonl
    if input_jsonl is None:
        input_jsonl = str(script_dir / "testcases" / "c2rust" / "cleaned_test_cases.jsonl")

    api_line_counts = args.api_line_counts
    if api_line_counts is None:
        api_line_counts = str(script_dir / "testcases" / "c2rust" / "api_lines.jsonl")

    cache_file = args.cache_file
    if cache_file is None:
        cache_file = Path(repo_root / "output" / "C2Rust" / args.model_name / f"test_results_cache_{args.model_name}.json")

    print(f"[CONFIG] Model: {args.model_name}")
    print(f"[CONFIG] C++ base: {cpp_base}")
    print(f"[CONFIG] Rust base: {rs_base}")
    print(f"[CONFIG] Input JSONL: {input_jsonl}")
    print(f"[CONFIG] API line counts: {api_line_counts}")
    print(f"[CONFIG] Cache file: {cache_file}")
    print(f"[CONFIG] Timeout: {args.timeout}s")
    print(f"[CONFIG] Docker image: {args.docker_image}")
    print()

    main(
        input_jsonl=input_jsonl,
        model_name=args.model_name,
        cpp_base=cpp_base,
        rs_base=rs_base,
        cache_file=cache_file,
        api_line_counts=api_line_counts,
        docker_image=args.docker_image
    )