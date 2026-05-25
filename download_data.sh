#!/bin/bash
# Alternative download script using huggingface-cli
# May work better in restricted network environments

OUTPUT_DIR="/root/codes/baidu_personal-code_self-reflection-moe/baidu/personal-code/self-reflection-moe/new/RepoZero"

# Download C2Rust
echo "Downloading RepoZero-C2Rust..."
huggingface-cli download jessezhaoxizhang/RepoZero-C2Rust --repo-type dataset --local-dir "$OUTPUT_DIR/RepoZero-C2Rust" --local-dir-use-symlinks False

# Extract zips in C2Rust
echo "Extracting zip files in RepoZero-C2Rust..."
find "$OUTPUT_DIR/RepoZero-C2Rust" -name "*.zip" -exec unzip -o {} -d "$(dirname {})" \;

# Download Py2JS
echo "Downloading RepoZero-Py2JS..."
huggingface-cli download jessezhaoxizhang/RepoZero-Py2JS --repo-type dataset --local-dir "$OUTPUT_DIR/RepoZero-Py2JS" --local-dir-use-symlinks False

# Extract zips in Py2JS
echo "Extracting zip files in RepoZero-Py2JS..."
find "$OUTPUT_DIR/RepoZero-Py2JS" -name "*.zip" -exec unzip -o {} -d "$(dirname {})" \;

echo "All downloads and extractions completed!"