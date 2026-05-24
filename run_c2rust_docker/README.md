# C2Rust Docker Implementation

This directory contains the Docker-based evaluation implementation for the C2Rust benchmark (C++ to Rust translation).

## Prerequisites

```bash
# Docker (latest)
docker --version

# Python 3.9+
python --version

# API credentials
export BASE_URL="https://openrouter.ai/api/v1/"
export API_KEY="your-api-key-here"
```

## Installation

```bash
cd RepoZero
pip install anthropic openai requests
```

## Quick Start

```bash
cd run_c2rust_docker

# Run with default settings (4 concurrent processes, deepseek-v3.2 model)
python run_all_docker.py

# Custom number of processes
python run_all_docker.py -k 8

# Custom model
export MODEL_NAME="deepseek-v3.1-250821"
python run_all_docker.py

# Custom Docker image
export REPOZERO_DOCKER_IMAGE="iregistry.baidu-int.com/repo_zero/c2rust-arena:fixed"
python run_all_docker.py
```

## Docker Environment

Each task runs in an isolated container with:

| Component | Path | Description |
|-----------|------|-------------|
| Workspace | `/workspace` | Working directory |
| Dataset | `/workspace/dataset` | Source files + pre-compiled executables |
| Output | `/output` | Generated Rust files |
| Network | `none` | Disabled for security |

## Implementation Details

### Container Lifecycle

1. **Create**: New container for each test case
2. **Setup**: Copy C++ source and pre-compiled executable into container
3. **Execute**: Run agent with access to the C++ binary for debugging
4. **Collect**: Copy generated Rust files back to host
5. **Cleanup**: Remove container

### Docker Image

The default image is `ghcr.io/jessezzzzz/c2rust-arena:latest`, which includes:
- C++ runtime libraries
- Multiple compiler support (gcc-8.2, gcc-12)
- All required shared libraries
- Custom library paths for compatibility

### Gold Repositories

The following repositories are evaluated:

| Repository | Description |
|------------|-------------|
| Clipper | Polygon clipping library |
| sortedcontainers-cpp | Sorted container implementations |
| color | Color manipulation library |
| indicators | Technical indicators for trading |
| earcut.hpp | Polygon triangulation |
| immer | Immutable data structures |
| hopscotch-map | Hash map implementation |
| url-parser | URL parsing library |
| inflection-cpp | String inflection utilities |
| idna-cpp | Internationalized domain names |

## Command Line Options

```
usage: run_all_docker.py [-h] [-k NUM_PROCESSES] [-m MODEL]

options:
  -h, --help            show this help message and exit
  -k NUM_PROCESSES, --num-processes NUM_PROCESSES
                        Number of concurrent processes (default: 4)
  -m MODEL, --model MODEL
                        Model name to use
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REPOZERO_DOCKER_IMAGE` | Docker image to use | `ghcr.io/jessezzzzz/c2rust-arena:latest` |
| `MODEL_NAME` | Model name for evaluation | `deepseek-v3.2` |
| `BASE_URL` | API base URL | `https://openrouter.ai/api/v1` |
| `API_KEY` | API key | — |

## Output Structure

```
C2Rust/
├── output_large/
│   └── <model_name>/
│       ├── packages/
│       │   ├── Clipper/
│       │   │   ├── test1_pkg/
│       │   │   │   ├── test1.rs
│       │   │   │   └── trajectory.jsonl
│       │   │   └── ...
│       │   └── ...
│       ├── progress.json
│       └── token_usage.log
└── cleaned_test_cases.jsonl
```

## Troubleshooting

### Container "not found" error

If you encounter errors with binaries not being found in containers, ensure you're using a Docker image with the necessary library compatibility:

```bash
# Build the fixed image if needed
cd run_c2rust_docker
docker build -t iregistry.baidu-int.com/repo_zero/c2rust-arena:fixed .
export REPOZERO_DOCKER_IMAGE="iregistry.baidu-int.com/repo_zero/c2rust-arena:fixed"
```

### Network isolation issues

The containers run with `--network none` for security. If you need network access for debugging, modify the `create_task_container` function to remove the network constraint.

## License

Dataset and code are released under [CC0 1.0](https://spdx.org/licenses/CC0-1.0).