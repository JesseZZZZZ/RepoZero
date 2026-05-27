import json
import os
import random
import argparse
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("[WARNING] numpy not found, Bootstrap CI calculation will be skipped")


# Default test files to evaluate
DEFAULT_VALID_IDS = [
    'boltons/test10.py', 'fractions/test14.py', 'deepdiff/test16.py', 'bech32/test4.py', 'idna/test13.py', 'base58/test6.py', 'bech32/test12.py', 'canonicaljson/test20.py', 'idna/test6.py', 'jsonschema/test7.py', 'schedule/test9.py', 'bidict/test5.py', 'mpmath/test4.py', 'furl/test5.py', 'furl/test11.py', 'bidict/test13.py', 'bech32/test2.py', 'networkx/test14.py', 'yaml/test16.py', 'bech32/test9.py', 'idna/test9.py', 'base58/test1.py', 'networkx/test5.py', 'moneyed/test6.py', 'bencoder/test7.py', 'pyaes/test10.py', 'markdown/test13.py', 'networkx/test4.py', 'bencoder/test15.py', 'jsonschema/test15.py', 'networkx/test16.py', 'markdown/test19.py', 'base58/test2.py', 'rsa/test15.py', 'construct/test12.py', 'rsa/test19.py', 'whoosh/test2.py', 'moneyed/test17.py', 'networkx/test13.py', 'networkx/test7.py', 'mpmath/test12.py', 'rsa/test8.py', 'canonicaljson/test14.py', 'networkx/test3.py', 'base58/test7.py', 'boltons/test14.py', 'boltons/test3.py', 'idna/test4.py', 'boltons/test11.py', 'mpmath/test1.py', 'base58/test19.py', 'moneyed/test3.py', 'bech32/test13.py', 'construct/test16.py', 'pyaes/test17.py', 'sqlparse/test4.py', 'jose/test7.py', 'idna/test18.py', 'jose/test13.py', 'whoosh/test7.py', 'bidict/test10.py', 'pyaes/test2.py', 'whoosh/test6.py', 'yaml/test2.py', 'deepdiff/test3.py', 'canonicaljson/test8.py', 'whoosh/test1.py', 'bencoder/test6.py', 'bidict/test17.py', 'moneyed/test15.py', 'pyaes/test12.py', 'idna/test11.py', 'deepdiff/test18.py', 'sqlparse/test2.py', 'rsa/test5.py', 'yaml/test11.py', 'canonicaljson/test11.py', 'schedule/test13.py', 'schedule/test2.py', 'jsonschema/test8.py', 'mpmath/test19.py', 'pyaes/test9.py', 'pyaes/test19.py', 'fractions/test15.py', 'markdown/test11.py', 'bidict/test16.py', 'construct/test20.py', 'yaml/test6.py', 'mpmath/test13.py', 'mpmath/test18.py', 'idna/test12.py', 'bech32/test15.py', 'yaml/test12.py', 'boltons/test15.py', 'deepdiff/test10.py', 'rsa/test16.py', 'boltons/test4.py', 'furl/test12.py', 'moneyed/test12.py', 'whoosh/test20.py', 'schedule/test19.py', 'bidict/test3.py', 'base58/test17.py', 'fractions/test2.py', 'moneyed/test7.py', 'whoosh/test3.py', 'mpmath/test7.py', 'construct/test17.py', 'idna/test15.py', 'mpmath/test17.py', 'markdown/test4.py', 'mpmath/test11.py', 'bech32/test1.py', 'bidict/test12.py', 'bencoder/test5.py', 'mpmath/test16.py', 'jose/test15.py', 'pyaes/test4.py', 'canonicaljson/test1.py', 'bech32/test14.py', 'moneyed/test14.py', 'jsonschema/test9.py', 'fractions/test19.py', 'construct/test19.py', 'yaml/test10.py', 'canonicaljson/test17.py', 'markdown/test7.py', 'schedule/test10.py', 'jsonschema/test10.py', 'mpmath/test15.py', 'bencoder/test8.py', 'bidict/test8.py', 'canonicaljson/test9.py', 'bencoder/test18.py', 'base58/test15.py', 'moneyed/test9.py', 'boltons/test6.py', 'boltons/test5.py', 'fractions/test6.py', 'jose/test9.py', 'yaml/test5.py', 'moneyed/test11.py', 'yaml/test7.py', 'bidict/test14.py', 'fractions/test5.py', 'boltons/test17.py', 'jsonschema/test20.py', 'deepdiff/test4.py', 'construct/test15.py', 'construct/test7.py', 'idna/test17.py', 'networkx/test6.py', 'whoosh/test18.py', 'jsonschema/test14.py', 'fractions/test4.py', 'jose/test10.py', 'rsa/test7.py', 'canonicaljson/test13.py', 'furl/test6.py', 'canonicaljson/test5.py', 'boltons/test7.py', 'yaml/test15.py', 'base58/test13.py', 'bencoder/test3.py', 'pyaes/test11.py', 'pbkdf2/test16.py', 'bech32/test3.py', 'jose/test12.py', 'moneyed/test19.py', 'deepdiff/test1.py', 'boltons/test9.py', 'markdown/test14.py', 'pyaes/test8.py', 'bencoder/test17.py', 'fractions/test1.py', 'schedule/test3.py', 'jose/test1.py', 'idna/test16.py', 'bech32/test11.py', 'jose/test6.py', 'base58/test9.py', 'mpmath/test3.py', 'bencoder/test13.py', 'bidict/test11.py', 'idna/test8.py', 'schedule/test6.py', 'bidict/test7.py', 'pbkdf2/test15.py', 'moneyed/test2.py', 'pbkdf2/test11.py', 'rsa/test11.py', 'jsonschema/test18.py', 'jsonschema/test6.py', 'base58/test12.py', 'yaml/test18.py', 'bencoder/test2.py', 'construct/test5.py', 'furl/test10.py', 'boltons/test1.py', 'deepdiff/test11.py', 'bech32/test8.py', 'furl/test9.py', 'fractions/test16.py', 'whoosh/test9.py', 'schedule/test18.py', 'bech32/test16.py', 'base58/test16.py', 'whoosh/test15.py', 'jsonschema/test2.py', 'schedule/test14.py', 'moneyed/test13.py', 'yaml/test9.py', 'jose/test19.py', 'bidict/test6.py', 'markdown/test12.py', 'base58/test14.py', 'whoosh/test4.py', 'bidict/test1.py', 'pyaes/test13.py', 'idna/test19.py', 'networkx/test15.py', 'idna/test2.py', 'pyaes/test7.py', 'bidict/test18.py', 'whoosh/test17.py', 'bencoder/test10.py', 'yaml/test20.py', 'bidict/test20.py', 'pyaes/test14.py', 'bencoder/test9.py', 'whoosh/test11.py', 'base58/test20.py', 'markdown/test16.py', 'furl/test3.py', 'furl/test2.py', 'yaml/test1.py', 'moneyed/test18.py', 'moneyed/test5.py', 'sqlparse/test9.py', 'whoosh/test14.py', 'schedule/test20.py', 'base58/test8.py', 'sqlparse/test16.py', 'idna/test7.py', 'idna/test20.py', 'pbkdf2/test13.py', 'furl/test4.py', 'construct/test18.py', 'jsonschema/test5.py', 'schedule/test12.py', 'bidict/test19.py', 'furl/test7.py', 'construct/test3.py', 'deepdiff/test15.py', 'markdown/test1.py', 'schedule/test4.py', 'jsonschema/test1.py', 'construct/test10.py', 'schedule/test16.py', 'construct/test14.py', 'bencoder/test11.py', 'schedule/test5.py', 'boltons/test19.py', 'bencoder/test14.py', 'jsonschema/test13.py', 'fractions/test13.py', 'schedule/test1.py', 'base58/test4.py', 'jose/test17.py', 'jsonschema/test19.py', 'bech32/test7.py', 'mpmath/test5.py', 'canonicaljson/test18.py', 'jose/test3.py', 'furl/test13.py', 'base58/test18.py', 'fractions/test20.py', 'jsonschema/test4.py', 'markdown/test15.py', 'markdown/test9.py', 'sqlparse/test3.py', 'boltons/test13.py', 'markdown/test6.py', 'markdown/test3.py', 'rsa/test18.py', 'fractions/test3.py', 'pyaes/test15.py', 'bencoder/test16.py', 'boltons/test2.py', 'fractions/test17.py', 'jose/test2.py', 'canonicaljson/test3.py', 'canonicaljson/test7.py', 'networkx/test2.py', 'pbkdf2/test7.py', 'yaml/test14.py', 'mpmath/test6.py', 'pyaes/test18.py', 'whoosh/test19.py', 'jsonschema/test12.py', 'moneyed/test1.py', 'pbkdf2/test14.py', 'whoosh/test16.py', 'deepdiff/test2.py', 'bencoder/test1.py', 'networkx/test17.py', 'construct/test1.py', 'pyaes/test16.py', 'markdown/test8.py', 'markdown/test17.py', 'canonicaljson/test15.py', 'construct/test6.py', 'jose/test4.py', 'pbkdf2/test8.py', 'bencoder/test12.py', 'rsa/test2.py', 'networkx/test20.py', 'canonicaljson/test16.py', 'construct/test8.py', 'pyaes/test5.py', 'yaml/test8.py', 'sqlparse/test10.py', 'idna/test3.py', 'schedule/test11.py', 'canonicaljson/test10.py', 'markdown/test2.py', 'mpmath/test9.py', 'bidict/test15.py', 'markdown/test5.py', 'canonicaljson/test2.py', 'boltons/test12.py', 'whoosh/test8.py', 'moneyed/test10.py', 'jsonschema/test11.py', 'canonicaljson/test19.py', 'pyaes/test6.py', 'pbkdf2/test1.py', 'pbkdf2/test4.py', 'sqlparse/test7.py', 'bidict/test4.py', 'furl/test1.py', 'markdown/test10.py', 'yaml/test17.py', 'base58/test11.py', 'jose/test8.py', 'rsa/test17.py', 'yaml/test4.py', 'idna/test10.py', 'furl/test8.py', 'construct/test4.py', 'jsonschema/test16.py', 'fractions/test12.py', 'bech32/test10.py', 'canonicaljson/test4.py', 'rsa/test10.py', 'bencoder/test4.py', 'bidict/test9.py', 'construct/test2.py', 'yaml/test19.py', 'pbkdf2/test2.py', 'fractions/test7.py', 'pbkdf2/test10.py', 'whoosh/test10.py', 'mpmath/test14.py', 'bidict/test2.py', 'idna/test1.py', 'networkx/test1.py', 'mpmath/test8.py', 'idna/test14.py', 'jsonschema/test3.py', 'base58/test10.py', 'deepdiff/test6.py', 'idna/test5.py', 'deepdiff/test12.py', 'moneyed/test8.py', 'canonicaljson/test6.py', 'fractions/test8.py', 'jose/test16.py', 'fractions/test9.py', 'mpmath/test10.py', 'networkx/test11.py', 'fractions/test11.py', 'markdown/test20.py', 'markdown/test18.py', 'bencoder/test19.py', 'base58/test3.py', 'yaml/test13.py', 'jose/test11.py', 'pbkdf2/test6.py', 'canonicaljson/test12.py', 'networkx/test10.py', 'schedule/test7.py', 'bech32/test17.py', 'moneyed/test20.py', 'bech32/test6.py', 'mpmath/test2.py', 'whoosh/test5.py', 'bech32/test5.py', 'moneyed/test16.py', 'base58/test5.py'
]

# Category library mapping
CATEGORY_LIBRARY_MAP = {
    "Serialization & Data Formats": [
        "bencoder", "canonicaljson", "jsonschema", "markdown", "sqlparse", "yaml"
    ],
    "Cryptography & Encoding": [
        "base58", "bech32", "jose", "pyaes", "pbkdf2", "rsa"
    ],
    "Data Structures & Utilities": [
        "bidict", "boltons", "construct", "deepdiff", "furl"
    ],
    "Math & Science": [
        "fractions", "mpmath", "networkx"
    ],
    "Specialized Tools": [
        "idna", "moneyed", "schedule", "whoosh"
    ]
}

# Library to category mapping
LIBRARY_TO_CATEGORY = {}
for category, libraries in CATEGORY_LIBRARY_MAP.items():
    for lib in libraries:
        LIBRARY_TO_CATEGORY[lib] = category


def calculate_bootstrap_ci(pass_rates, n_bootstrap=1000, confidence=0.95):
    """
    Calculate Bootstrap Confidence Interval.

    Args:
        pass_rates: List of all test case pass rates
        n_bootstrap: Number of bootstrap samples (default: 1000)
        confidence: Confidence level (default: 0.95)

    Returns:
        dict: Contains mean, standard deviation, CI lower and upper bounds
    """
    if not HAS_NUMPY or not pass_rates:
        return {
            'mean': 0.0,
            'std': 0.0,
            'ci_lower': 0.0,
            'ci_upper': 0.0
        }

    pass_rates = np.array(pass_rates)
    n_samples = len(pass_rates)

    # Resample n_bootstrap times and calculate mean each time
    bootstrap_means = []
    for _ in range(n_bootstrap):
        # Resample with replacement
        sample_indices = np.random.choice(n_samples, size=n_samples, replace=True)
        sample = pass_rates[sample_indices]
        bootstrap_means.append(np.mean(sample))

    bootstrap_means = np.array(bootstrap_means)

    # Calculate confidence interval
    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_means, alpha / 2 * 100)
    ci_upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)

    return {
        'mean': np.mean(bootstrap_means),
        'std': np.std(bootstrap_means),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper
    }


def calculate_all_pass_average(results_dir):
    """
    Calculate micro and macro pass rates for all test classes by category.

    Args:
        results_dir: Directory path containing evaluation results

    Returns:
        dict: Dictionary containing various statistics
    """
    results = []
    all_pass_rates = []
    test_case_pass_rates = []

    # Results by category
    results_by_category = {category: [] for category in CATEGORY_LIBRARY_MAP.keys()}

    # Collect all test case pass rates for bootstrap calculation
    all_test_case_pass_rates = []

    # Collect all all pass values (0 or 1) for bootstrap calculation
    all_pass_values = []

    # Pre-calculate total tests per library from DEFAULT_VALID_IDS
    library_total_tests = {}
    for test_id in DEFAULT_VALID_IDS:
        lib_name = test_id.split('/')[0]
        library_total_tests[lib_name] = library_total_tests.get(lib_name, 0) + 1

    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith('testcase_') and filename.endswith('_file_pass_rates.json'):
            # Extract class name (library name)
            class_name = filename.replace('testcase_', '').replace('_file_pass_rates.json', '')
            # Handle merged suffix
            if class_name.endswith('_merged'):
                class_name = class_name[:-7]
            if class_name in ['ecdsa', 'rlp', 'bitstring', 'bitarray']:
                continue

            filepath = os.path.join(results_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Use total tests from DEFAULT_VALID_IDS for this library
            total_tests = library_total_tests.get(class_name, len(data))

            # all_pass statistics: all test cases pass counts as pass
            all_pass_count = sum(1 for v in data.values() if v.get('pass_rate') == 1.0)
            all_pass_rate = all_pass_count / total_tests if total_tests > 0 else 0

            # test_case_pass statistics: average pass rate of individual test cases
            # Divide by DEFAULT_VALID_IDS count for this library, not actual data count
            test_case_pass_rates_list = [v.get('pass_rate', 0) for v in data.values()]
            test_case_pass_rate = sum(test_case_pass_rates_list) / total_tests if total_tests > 0 else 0

            # Collect all test case pass rates
            for test_file, test_data in data.items():
                if test_file in DEFAULT_VALID_IDS:
                    all_test_case_pass_rates.append(test_data.get('pass_rate', 0))
                    # all pass 1 means all passed, 0 means not all passed
                    all_pass_values.append(1 if test_data.get('pass_rate') == 1.0 else 0)

            result_item = {
                'class': class_name,
                'total_tests': total_tests,
                'all_pass_count': all_pass_count,
                'all_pass_rate': all_pass_rate,
                'test_case_pass_rate': test_case_pass_rate
            }
            results.append(result_item)

            all_pass_rates.append(all_pass_rate)
            test_case_pass_rates.append(test_case_pass_rate)

            # Classify by category - determine category based on library name
            for test_file in data.keys():
                # Classify by category - determine category based on library name
                lib_name = test_file.split('/')[0]
                category = LIBRARY_TO_CATEGORY.get(lib_name)
                if category and test_file in DEFAULT_VALID_IDS:
                    test_status = data[test_file].get('pass_rate') == 1.0
                    results_by_category[category].append({
                        'class': class_name,
                        'file': test_file,
                        'pass': test_status,
                        'pass_rate': data[test_file].get('pass_rate', 0)
                    })

    # Calculate micro and macro pass rates
    if results:
        total_tests = sum(r['total_tests'] for r in results)
        total_all_pass = sum(r['all_pass_count'] for r in results)

        # micro pass rate: calculated based on all samples
        micro_all_pass_rate = total_all_pass / total_tests
        # macro pass rate: average of class pass rates
        macro_all_pass_rate = sum(all_pass_rates) / len(all_pass_rates)

        # test_case_pass micro and macro
        micro_test_case_pass_rate = sum(r['test_case_pass_rate'] * r['total_tests'] for r in results) / total_tests
        macro_test_case_pass_rate = sum(test_case_pass_rates) / len(test_case_pass_rates)

        # Calculate micro all pass by category
        micro_all_pass_by_category = {}
        for category in CATEGORY_LIBRARY_MAP.keys():
            cat_results = results_by_category[category]
            if cat_results:
                passed = sum(1 for r in cat_results if r['pass'])
                total = len(cat_results)
                micro_all_pass_by_category[category] = passed / total
            else:
                micro_all_pass_by_category[category] = 0.0

        # Calculate micro test_case_pass by category
        micro_test_case_pass_by_category = {}
        for category in CATEGORY_LIBRARY_MAP.keys():
            cat_results = results_by_category[category]
            if cat_results:
                total_pass_rate = sum(r['pass_rate'] for r in cat_results)
                total = len(cat_results)
                micro_test_case_pass_by_category[category] = total_pass_rate / total
            else:
                micro_test_case_pass_by_category[category] = 0.0

        # Calculate Bootstrap Confidence Interval
        bootstrap_ci = calculate_bootstrap_ci(all_test_case_pass_rates, n_bootstrap=1000, confidence=0.95)

        # Calculate All Pass Bootstrap Confidence Interval
        all_pass_bootstrap_ci = calculate_bootstrap_ci(all_pass_values, n_bootstrap=1000, confidence=0.95)

        stats = {
            'results': results,
            'micro_all_pass_rate': micro_all_pass_rate,
            'macro_all_pass_rate': macro_all_pass_rate,
            'micro_test_case_pass_rate': micro_test_case_pass_rate,
            'macro_test_case_pass_rate': macro_test_case_pass_rate,
            'micro_all_pass_by_category': micro_all_pass_by_category,
            'micro_test_case_pass_by_category': micro_test_case_pass_by_category,
            'results_by_category': results_by_category,
            'total_tests': total_tests,
            'total_all_pass': total_all_pass,
            'num_classes': len(results),
            'bootstrap_ci': bootstrap_ci,
            'all_pass_bootstrap_ci': all_pass_bootstrap_ci
        }
    else:
        stats = {
            'results': results,
            'micro_all_pass_rate': 0,
            'macro_all_pass_rate': 0,
            'micro_test_case_pass_rate': 0,
            'macro_test_case_pass_rate': 0,
            'micro_all_pass_by_category': {category: 0.0 for category in CATEGORY_LIBRARY_MAP.keys()},
            'micro_test_case_pass_by_category': {category: 0.0 for category in CATEGORY_LIBRARY_MAP.keys()},
            'results_by_category': {category: [] for category in CATEGORY_LIBRARY_MAP.keys()},
            'total_tests': 0,
            'total_all_pass': 0,
            'num_classes': 0,
            'bootstrap_ci': {'mean': 0.0, 'std': 0.0, 'ci_lower': 0.0, 'ci_upper': 0.0},
            'all_pass_bootstrap_ci': {'mean': 0.0, 'std': 0.0, 'ci_lower': 0.0, 'ci_upper': 0.0}
        }

    return stats


def print_all_pass_stats(stats):
    """
    Print evaluation statistics.

    Args:
        stats: Statistics dictionary from calculate_all_pass_average
    """
    print(f"\n{'Class':<20} {'Total Tests':<10} {'All Pass':<10} {'Test Case Pass':<15}")
    print("-" * 70)
    for r in stats['results']:
        print(f"{r['class']:<20} {r['total_tests']:<10} {r['all_pass_count']:<10} "
              f"{r['all_pass_rate']:<12.4f} {r['test_case_pass_rate']:<15.4f}")

    # Statistics by category
    print("\n===== Statistics by Category =====")
    total_category_samples = sum(len(stats['results_by_category'][c]) for c in CATEGORY_LIBRARY_MAP.keys())
    print(f"\n{'Category':<35} {'Samples':<10} {'Ratio':<10} {'All Pass Avg':<18} {'Test Case Pass Avg':<20}")
    print("-" * 95)
    for category in CATEGORY_LIBRARY_MAP.keys():
        count = len(stats['results_by_category'][category])
        ratio = count / total_category_samples if total_category_samples > 0 else 0
        all_pass_avg = stats['micro_all_pass_by_category'][category]
        test_case_pass_avg = stats['micro_test_case_pass_by_category'][category]
        print(f"{category:<35} {count:<10} {ratio:<10.4f} {all_pass_avg:<18.4f} {test_case_pass_avg:<20.4f}")
    print("-" * 95)

    # Print micro and macro pass rates
    print("\n===== Micro/Macro Pass Rates =====")
    print(f"\nAll Pass (all test cases passed):")
    print(f"  Micro rate: {stats['micro_all_pass_rate']:.4f} (based on all samples)")
    print(f"  Macro rate: {stats['macro_all_pass_rate']:.4f} (average of classes)")

    print(f"\nTest Case Pass (average test case pass rate):")
    print(f"  Micro rate: {stats['micro_test_case_pass_rate']:.4f} (based on all samples)")
    print(f"  Macro rate: {stats['macro_test_case_pass_rate']:.4f} (average of classes)")

    print(f"\nTotal:")
    print(f"  Number of test classes: {stats['num_classes']}")
    print(f"  Total test samples: {stats['total_tests']}")
    print(f"  Total all-pass samples: {stats['total_all_pass']}")



def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate detailed evaluation statistics for C2Rust translation results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate statistics for a specific model
  python calculate_all_pass_c2rust.py -m deepseek-v3.2

  # Calculate with custom results directory
  python calculate_all_pass_c2rust.py --results-dir ./C2Rust/output/results/deepseek-v3.2_docker

  # Use fewer bootstrap samples for faster calculation
  python calculate_all_pass_c2rust.py -n-bootstrap 100
        """
    )
    parser.add_argument(
        "-m", "--model-name",
        type=str,
        required=True,
        help="Model name to calculate statistics for (required)"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Directory containing evaluation results (default: ./C2Rust/output/results/<model>_docker)"
    )
    parser.add_argument(
        "-n", "--n-bootstrap",
        type=int,
        default=1000,
        help="Number of bootstrap samples for CI calculation (default: 1000)"
    )

    args = parser.parse_args()

    # Set default results directory based on model name
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    results_dir = args.results_dir
    if results_dir is None:
        results_dir = str(repo_root / "C2Rust" / "output" / "results" / f"{args.model_name}_docker")

    print(f"[CONFIG] Model: {args.model_name}")
    print(f"[CONFIG] Results directory: {results_dir}")
    print(f"[CONFIG] Bootstrap samples: {args.n_bootstrap}")
    print()

    if not os.path.exists(results_dir):
        print(f"[ERROR] Results directory not found: {results_dir}")
        return

    stats = calculate_all_pass_average(results_dir)
    print_all_pass_stats(stats)


if __name__ == "__main__":
    main()