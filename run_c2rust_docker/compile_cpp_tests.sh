#!/bin/bash
# Compile C++ test files for Linux x86_64 inside Docker container

set -e

DOCKER_IMAGE="iregistry.baidu-int.com/repo_zero/c2rust-arena:latest"
HOST_DATASET_ROOT="/root/codes/baidu_personal-code_self-reflection-moe/baidu/personal-code/self-reflection-moe/RepoZero/C2Rust/CppLarge"
HOST_OUTPUT_ROOT="/root/codes/baidu_personal-code_self-reflection-moe/baidu/personal-code/self-reflection-moe/RepoZero/C2Rust/CppLarge"
CONTAINER_WORKSPACE="/workspace"
CONTAINER_DATASET_ROOT="${CONTAINER_WORKSPACE}/dataset"

# Gold repos
GOLD_REPOS=(
    "Clipper"
    "sortedcontainers-cpp"
    "color"
    "indicators"
    "earcut.hpp"
    "immer"
    "hopscotch-map"
    "url-parser"
    "inflection-cpp"
    "idna-cpp"
)

# Function to compile a single C++ file
compile_cpp() {
    local repo_name=$1
    local test_file=$2
    local relative_path="${repo_name}/${test_file}"
    local module_name=$(basename "$test_file" .cpp)
    local output_name="${module_name}_executable"

    # Determine test file location (could be in tests/ subdir or root)
    local host_cpp_path
    if [[ -f "${HOST_DATASET_ROOT}/${repo_name}/tests/${test_file}" ]]; then
        host_cpp_path="${HOST_DATASET_ROOT}/${repo_name}/tests/${test_file}"
    else
        host_cpp_path="${HOST_DATASET_ROOT}/${repo_name}/${test_file}"
    fi

    if [[ ! -f "$host_cpp_path" ]]; then
        echo "[SKIP] $relative_path not found"
        return 1
    fi

    # Run compiler in Docker
    echo "[COMPILE] $relative_path -> $output_name"

    docker run --rm \
        -v "${HOST_DATASET_ROOT}:/workspace/dataset" \
        -w "/workspace/dataset/${repo_name}" \
        ${DOCKER_IMAGE} \
        bash -c "
        g++ -std=c++17 -O2 -o ${output_name} ${test_file} -lm -pthread 2>&1 || \
        g++ -std=c++17 -O2 -o ${output_name} tests/${test_file} -lm -pthread 2>&1 || \
        g++ -std=c++17 -O2 -o tests/${output_name} tests/${test_file} -lm -pthread 2>&1
        " && echo "[OK] $relative_path" || echo "[FAIL] $relative_path"
}

# Main compilation loop
cd "$HOST_DATASET_ROOT"

for repo in "${GOLD_REPOS[@]}"; do
    if [[ ! -d "$repo" ]]; then
        echo "[SKIP] Repo not found: $repo"
        continue
    fi

    echo "===== Compiling $repo ====="

    # Find all test*.cpp files (in tests/ dir or root)
    test_files=$(find "$repo" -name "test*.cpp" -type f 2>/dev/null || true)

    for test_file in $test_files; do
        # Get relative path from repo root
        rel_path=${test_file#$repo/}
        compile_cpp "$repo" "$rel_path"
    done
done

echo "===== Compilation complete ====="

# Show summary of generated executables
echo ""
echo "Generated executables:"
find "$HOST_DATASET_ROOT" -name "*_executable" -type f 2>/dev/null | while read exe; do
    echo "  $exe"
    file "$exe"
done