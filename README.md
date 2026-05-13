# RepoZero

**🐳 Docker implementation now available!** See [Py2JS Docker](#py2js-docker-implementation) section below for the latest Docker-based evaluation.

**RepoZero** is a benchmark dataset and evaluation suite for assessing the ability of large language models to perform *zero-shot repository-level code translation* — migrating entire real-world library codebases across programming language ecosystems.

RepoZero covers two translation tasks:

| Task | Source | Target | Libraries | Test Files |
|------|--------|--------|-----------|------------|
| **C2Rust** | C++ | Rust | 11 | 200 |
| **Py2JS** | Python | JavaScript (Node.js ESM) | 24 | 400 |

Total benchmark: **600 test files** across **35 open-source libraries**.

---

## Quick Start: Py2JS Docker Implementation

The Docker implementation provides an isolated, reproducible environment for running Py2JS evaluations with pre-built Docker images containing Python test executables.

### Prerequisites

```bash
# Docker (latest)
docker --version

# Python 3.9+
python --version

# OpenAI-compatible API credentials
export BASE_URL="https://openrouter.ai/api/v1/"
export API_KEY="your-api-key-here"
```

### Installation

```bash
git clone https://github.com/JesseZZZZZ/RepoZero.git
cd RepoZero
# this step can be skipped, because RepoZero requires limited number of packages, you can directly install them using the base environment
conda create -n repozero python==3.10
# only these packages are required
pip install openai requests anthropic
```
## Repository Structure
❗️Please mannually download [the dataset](https://disk.pku.edu.cn/link/AA0A7B7864999C4F84A0FCDF1C2C0A57BF) and place it at the root dir, the final directory should be like this⬇️
```
├── crossant.json                  # Croissant metadata descriptor (MLCommons)
│
├── C2Rust/
│   ├── CppLarge/                  # C++ source libraries (11 repos)
│   │   ├── Clipper/
│   │   ├── color/
│   │   ├── earcut.hpp/
│   │   ├── exprtk/
│   │   ├── hopscotch-map/
│   │   ├── idna-cpp/
│   │   ├── immer/
│   │   ├── indicators/
│   │   ├── inflection-cpp/
│   │   ├── sortedcontainers-cpp/
│   │   └── url-parser/
│   └── cleaned_test_cases.jsonl   # Test case parameters for C2Rust evaluation
│
├── Py2JS/
│   ├── dataset/                   # Python source files (24 libraries, 20 test files each)
│   │   ├── base58/  bech32/  bencoder/  bidict/  bitarray/  bitstring/
│   │   ├── boltons/  canonicaljson/  construct/  deepdiff/  ecdsa/
│   │   ├── fractions/  furl/  idna/  jose/  jsonschema/  markdown/
│   │   ├── moneyed/  mpmath/  networkx/  pbkdf2/  pyaes/  rsa/
│   │   ├── rlp/  schedule/  sqlparse/  whoosh/  yaml/
│   │   └── testcases_60/              # Test case parameter JSONL files (28 libraries)
│
├── evaluate/
├── run_c2rust/
├── run_py2js/                    # Local Py2JS (non-Docker) implementation
└── run_py2js_docker/            # 🐳 Docker-based Py2JS implementation
    ├── run_all_docker.py         # Main Docker evaluation script
    ├── run_terminal_agent.py    # Docker terminal agent core
    └── README.md                # Docker documentation
```

---

### Running Docker Evaluation

```bash
cd run_py2js_docker

# Run with default settings (4 concurrent processes, deepseek-v3.2 model)
python run_all_docker.py

# Custom number of processes
python run_all_docker.py -k 8

# Custom model
python run_all_docker.py -m deepseek-v3.1-250821

# Custom Docker image (if you've built your own)
export REPOZERO_DOCKER_IMAGE="my-custom-image:latest"
python run_all_docker.py
```

### Docker Implementation Details

The Docker implementation uses:

- **Image**: `ghcr.io/jessezzzzz/repoarena-new:latest` (pre-built with Python test executables)
- **Isolation**: Network-disabled containers (`--network none`) for security
- **File Handling**: Source files and pre-compiled executables are copied into containers
- **Output**: Generated JavaScript files are copied back to host after processing

### Docker Environment

Each task runs in an isolated container with:

- **Workspace**: `/workspace`
- **Dataset**: `/workspace/dataset` (source files + executables)
- **Output**: `/output` (generated JavaScript files)
- **Node.js**: Available for running generated code


---

## Benchmark Tasks

### C2Rust — C++ to Rust Translation

Translate C++ library implementations into idiomatic, correct Rust. The model must:
- Re-implement the library logic using Rust-native idioms and standard crates
- Match the I/O behavior of the original C++ test programs exactly
- Avoid directly wrapping the C++ source (zero-shot black-box translation)

**Libraries (11):** Clipper, color, earcut.hpp, exprtk, hopscotch-map, idna-cpp, immer, indicators, inflection-cpp, sortedcontainers-cpp, url-parser

### Py2JS — Python to JavaScript Translation

Translate Python library implementations into Node.js ES Module (`.mjs`) equivalents. The model must:
- Re-implement using only Node.js built-in modules (no npm packages)
- Accept identical CLI arguments and produce byte-for-byte identical stdout
- Use ESM syntax (`import`/`export`), no CommonJS

**Libraries (24):** base58, bech32, bencoder, bidict, bitarray, bitstring, boltons, canonicaljson, construct, deepdiff, ecdsa, fractions, furl, idna, jose, jsonschema, markdown, moneyed, mpmath, networkx, pbkdf2, pyaes, rsa, schedule, sqlparse, whoosh, yaml

**Category Groups:**
- **Serialization & Data Formats**: bencoder, canonicaljson, jsonschema, markdown, sqlparse, yaml
- **Cryptography & Encoding**: base58, bech32, jose, pyaes, pbkdf2, rsa
- **Data Structures & Utilities**: bidict, boltons, construct, deepdiff, furl
- **Math & Science**: fractions, mpmath, networkx
- **Specialized Tools**: idna, moneyed, schedule, whoosh

---

## Evaluation Metrics

All evaluation scripts report two metrics:

| Metric | Description |
|--------|-------------|
| **All-Pass Rate** | Fraction of source files where *all* test cases pass |
| **Test-Case Pass Rate** | Mean per-file fraction of passing test cases |

---

## Running the Benchmark

### Prerequisites

```bash
# Python 3.9+
pip install anthropic openai

# Node.js 18+ (for Py2JS evaluation)
node --version

# Optional: numpy for bootstrap CI (required by calculate_all_pass.py)
pip install numpy
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_BASE_URL` | Custom Anthropic API endpoint | Anthropic default |
| `BASE_URL` | OpenAI-compatible API base URL | `https://openrouter.ai/api/v1` |
| `API_KEY` | API key for OpenAI-compatible endpoint | — |
| `MODEL_NAME` | Model name to use | `deepseek-v3.2` |
| `PYTHON_BIN` | Python interpreter for evaluation | `python3` |
| `NODE_BIN` | Node.js interpreter for evaluation | `node` |
| `REPOZERO_DOCKER_IMAGE` | Docker image to use | `ghcr.io/jessezzzzz/repoarena-new:latest` |

### Run C2Rust

```bash
# Terminal agent — OpenAI-compatible API
cd run_c2rust
python run_all_openai.py

# Terminal agent — Anthropic API
python run_all_anthropic.py

# mini-swe-agent harness
python run_mini_swe_agent_anthropic.py
```

### Run Py2JS (Local)

```bash
# Terminal agent — OpenAI-compatible API
cd run_py2js
python run_all_openai.py

# Terminal agent — Anthropic API
python run_all_anthropic.py

# Iterative self-repair loop (generates test cases, attempts fixes up to N times)
python run_all_loop_openai.py

# Loop mode via mini-swe-agent
python run_all_loop_mini_openai.py
```

### Run Py2JS (Docker)

```bash
cd run_py2js_docker

# Run with default settings
python run_all_docker.py

# Custom number of processes
python run_all_docker.py -k 8

# Custom model
python run_all_docker.py -m deepseek-v3.1-250821

# Custom Docker image (if you've built your own)
export REPOZERO_DOCKER_IMAGE="my-custom-image:latest"
python run_all_docker.py
```

To override the model name, edit the `model_name` variable at the top of the relevant script, or (for scripts that support it) pass `-m <model>` on the command line.

### Evaluate Results

```bash
# Evaluate Py2JS terminal-agent output
python evaluate/eval_py2js.py -m <model_name>

# Evaluate Py2JS mini-swe-agent / loop output
python evaluate/eval_py2js_mini.py -m <model_name>

# Evaluate Py2JS Docker output
python evaluate/eval_py2js_docker.py -m <model_name>

# Calculate detailed statistics (with Bootstrap CI)
python evaluate/calculate_all_pass.py -m <model_name>

# Evaluate C2Rust terminal-agent output
python evaluate/eval_c2rust.py -m <model_name>

# Evaluate C2Rust mini-swe-agent output
python evaluate/eval_c2rust_mini.py -m <model_name>
```

Optional flags (all eval scripts):

```
--jsonl-dir      Directory containing .jsonl test-case files
                 (default: <task>/testcases or <task>/testcases_60)
--dataset-root   Root directory of the source dataset
                 (default: <task>/dataset or C2Rust/CppLarge)
```

Results are written to `evaluate/results/<model_name>/` as JSON files with per-file pass rates.

### Calculate Detailed Statistics

```bash
# Calculate statistics for a specific model
python evaluate/calculate_all_pass.py -m deepseek-v3.2

# Calculate with custom results directory
python evaluate/calculate_all_pass.py --results-dir ./Py2JS/output/results/deepseek-v3.2_docker

# Use fewer bootstrap samples for faster calculation
python evaluate/calculate_all_pass.py -n-bootstrap 100
```

This script provides:
- **Per-class statistics**: Pass rates for each test class (library)
- **Category-level breakdown**: Statistics grouped by library categories
  - Serialization & Data Formats
  - Cryptography & Encoding
  - Data Structures & Utilities
  - Math & Science
  - Specialized Tools
- **Micro/Macro rates**: Both all-pass and test-case-pass rates
- **Bootstrap Confidence Intervals**: 95% CI for both metrics

---

## Output Directory Layout

Run scripts write translated files to the following locations:

| Script type | Output path |
|-------------|-------------|
| Terminal agent (Py2JS) | `Py2JS/output/<model_name>/testfiles/` |
| mini-swe-agent (Py2JS) | `Py2JS/output_mini/<model_name>/testfiles/` |
| Loop — terminal agent | `Py2JS/output_loop/<model_name>_retry<N>/testfiles/` |
| Loop — mini-swe-agent | `Py2JS/output_loop_mini/<model_name>_retry<N>/testfiles/` |
| Docker (Py2JS) | `Py2JS/output/<model_name>/packages/` |
| Terminal agent (C2Rust) | `C2Rust/output/<model_name>/testfiles/` |
| mini-swe-agent (C2Rust) | `C2Rust/output_mini/<model_name>/testfiles/` |

Library helper files are written alongside under a `packages/` subdirectory.

---

## Dataset Format

### `gold_test_files.jsonl`

Each line is a JSON object identifying a benchmark test file:

```json
{"category": "C2Rust", "filename": "test20.cpp", "path": "C2Rust/CppLarge/Clipper/tests/test20.cpp", "library": "Clipper"}
{"category": "Py2JS",  "filename": "test1.py",   "path": "Py2JS/dataset/base58/test1.py",            "library": "base58"}
```

### Test-case JSONL files

Each line contains CLI argument parameters for one test invocation of a source file:

```json
{"filename": "base58/test1.py", "a": "1234567890"}
{"filename": "base58/test1.py", "a": "5kfxvzBm43bWNCpsa3B3dt5uXuced"}
```

The evaluation harness runs both the original source file and the translated file with these arguments and compares stdout line by line.

---

## License

Dataset and code are released under [CC0 1.0](https://spdx.org/licenses/CC0-1.0). All source code used in the benchmark is derived from open-source repositories; their original licenses remain in effect within their respective directories.
