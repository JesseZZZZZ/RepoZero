#!/usr/bin/env python3
"""
Download and extract datasets from HuggingFace for RepoZero.
Supports both RepoZero-Py2JS and RepoZero-C2Rust.
"""

import os
import time
import zipfile
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download, login


def extract_all_zips(directory: Path):
    """Extract all .zip files in the directory and its subdirectories."""
    print(f"\nExtracting zip files in {directory}...")
    zip_files = list(directory.rglob("*.zip"))
    print(f"Found {len(zip_files)} zip files")

    for zip_path in zip_files:
        print(f"Extracting {zip_path.name}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(zip_path.parent)
            print(f"  -> Extracted to {zip_path.parent}")
        except Exception as e:
            print(f"  -> Error extracting {zip_path}: {e}")


def download_with_retry(repo_id: str, local_dir: Path, max_retries: int = 3):
    """Download dataset with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}: Downloading {repo_id}...")
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(local_dir),
                repo_type="dataset",
                max_workers=4,
            )
            print(f"Successfully downloaded to {local_dir}")
            return local_dir
        except Exception as e:
            print(f"  -> Error: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  -> Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"  -> Failed after {max_retries} attempts")
                raise


def download_repozero_c2rust(output_dir: Path):
    """Download RepoZero-C2Rust dataset from HuggingFace."""
    print("Downloading RepoZero-C2Rust from HuggingFace...")
    c2rust_dir = output_dir / "C2Rust"
    return download_with_retry("jessezhaoxizhang/RepoZero-C2Rust", c2rust_dir)


def download_repozero_py2js(output_dir: Path):
    """Download RepoZero-Py2JS dataset from HuggingFace."""
    print("Downloading RepoZero-Py2JS from HuggingFace...")
    py2js_dir = output_dir / "Py2JS"
    return download_with_retry("jessezhaoxizhang/RepoZero-Py2JS", py2js_dir)


def main():
    # Output directory
    output_dir = Path("./")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download C2Rust first (as requested)
    c2rust_dir = download_repozero_c2rust(output_dir)
    extract_all_zips(c2rust_dir)

    # Download Py2JS
    py2js_dir = download_repozero_py2js(output_dir)
    extract_all_zips(py2js_dir)

    print("\nAll downloads and extractions completed!")


if __name__ == "__main__":
    main()