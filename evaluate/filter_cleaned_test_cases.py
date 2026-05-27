#!/usr/bin/env python3
"""
Filter cleaned_test_cases.jsonl to keep only rows whose file_name exists in api_lines.jsonl's file field.
"""

import json
from pathlib import Path


def filter_cleaned_test_cases(cleaned_file, api_lines_file, output_file):
    """
    Filter cleaned_test_cases.jsonl to keep only rows where file_name exists in api_lines.jsonl.

    Args:
        cleaned_file: Path to cleaned_test_cases.jsonl
        api_lines_file: Path to api_lines.jsonl
        output_file: Path to write the filtered results
    """
    # Read all file values from api_lines.jsonl
    api_files = set()
    with open(api_lines_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if 'file' in data:
                        api_files.add(data['file'])
                except json.JSONDecodeError:
                    continue

    print(f"Loaded {len(api_files)} unique files from api_lines.jsonl")

    # Filter cleaned_test_cases.jsonl
    kept_count = 0
    total_count = 0
    with open(cleaned_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if line:
                total_count += 1
                try:
                    data = json.loads(line)
                    if 'file_name' in data and data['file_name'] in api_files:
                        outfile.write(line + '\n')
                        kept_count += 1
                except json.JSONDecodeError:
                    continue

    print(f"Total lines processed: {total_count}")
    print(f"Lines kept: {kept_count}")
    print(f"Lines removed: {total_count - kept_count}")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    base_dir = Path("/root/codes/baidu_personal-code_self-reflection-moe/baidu/personal-code/self-reflection-moe/new/RepoZero/evaluate/testcases/c2rust")

    cleaned_file = base_dir / "cleaned_test_cases.jsonl"
    api_lines_file = base_dir / "api_lines.jsonl"
    output_file = base_dir / "cleaned_test_cases_filtered.jsonl"

    filter_cleaned_test_cases(cleaned_file, api_lines_file, output_file)