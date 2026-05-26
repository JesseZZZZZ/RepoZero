#!/usr/bin/env python3
"""
Download and extract datasets from HuggingFace or ModelScope for RepoZero.
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


def download_from_huggingface(output_dir: Path):
    """Download RepoZero datasets from HuggingFace."""
    # Download C2Rust first (as requested)
    print("Downloading RepoZero-C2Rust from HuggingFace...")
    c2rust_dir = output_dir / "C2Rust"
    download_with_retry("jessezhaoxizhang/RepoZero-C2Rust", c2rust_dir)
    extract_all_zips(c2rust_dir)

    # Download Py2JS
    print("Downloading RepoZero-Py2JS from HuggingFace...")
    py2js_dir = output_dir / "Py2JS"
    download_with_retry("jessezhaoxizhang/RepoZero-Py2JS", py2js_dir)
    extract_all_zips(py2js_dir)


def download_from_modelscope(output_dir: Path):
    """Download RepoZero datasets from ModelScope."""
    try:
        from modelscope import snapshot_download as ms_snapshot_download
    except ImportError:
        print("Error: modelscope library not found. Install with: pip install modelscope")
        raise

    # Download C2Rust
    print("Downloading RepoZero-C2Rust from ModelScope...")
    c2rust_dir = output_dir / "C2Rust"
    c2rust_dir.mkdir(parents=True, exist_ok=True)
    try:
        ms_snapshot_download(
            repo_id="JesseZhaoxiZhang/RepoZero-C2Rust",
            cache_dir=str(c2rust_dir),
        )
        print(f"Successfully downloaded to {c2rust_dir}")
        extract_all_zips(c2rust_dir)
    except Exception as e:
        print(f"Error downloading RepoZero-C2Rust: {e}")

    # Download Py2JS
    print("Downloading RepoZero-Py2JS from ModelScope...")
    py2js_dir = output_dir / "Py2JS"
    py2js_dir.mkdir(parents=True, exist_ok=True)
    try:
        ms_snapshot_download(
            repo_id="JesseZhaoxiZhang/RepoZero-Py2JS",
            cache_dir=str(py2js_dir),
        )
        print(f"Successfully downloaded to {py2js_dir}")
        extract_all_zips(py2js_dir)
    except Exception as e:
        print(f"Error downloading RepoZero-Py2JS: {e}")


def main():
    import sys

    # Output directory
    output_dir = Path("./")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Choose download source
    source = sys.argv[1] if len(sys.argv) > 1 else "huggingface"

    if source == "huggingface":
        download_from_huggingface(output_dir)
    elif source == "modelscope":
        download_from_modelscope(output_dir)
    else:
        print(f"Unknown source: {source}. Use 'huggingface' or 'modelscope'")
        sys.exit(1)

    print("\nAll downloads and extractions completed!")


if __name__ == "__main__":
    main()