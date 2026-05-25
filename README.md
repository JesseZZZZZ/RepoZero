<div align="center">
<a href="https://github.com/JesseZZZZZ/RepoZero">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="imgs/icon_repozero">
    <img alt="RepoZero" src="imgs/icon_repozero.png" width="500">
  </picture>
</a>
<br><br>

[![arXiv](https://img.shields.io/badge/RepoZero-arxiv-red)](https://arxiv.org/pdf/2605.07122)
[![HuggingFace-C2Rust](https://img.shields.io/badge/C2Rust-HF-yellow?logo=huggingface)](jessezhaoxizhang/RepoZero-C2Rust)
[![HuggingFace-Py2JS](https://img.shields.io/badge/Py2JS-HF-yellow?logo=huggingface)](jessezhaoxizhang/RepoZero-Py2JS)
[![Project Page](https://img.shields.io/badge/Homepage-gray?logo=homepage
)](https://repozero.osslab-pku.org/)


</div>
## 🎉 News

**Docker implementation now available for all benchmark tasks!**

- 🐳 **C2Rust Docker**: Complete Docker-based evaluation for C++ to Rust translation
- 🐳 **Py2JS Docker**: Complete Docker-based evaluation for Python to JavaScript translation
- ✅ **Reproducible**: Isolated, containerized environments for consistent results
- ✅ **Easy setup**: Pre-built Docker images with all dependencies

---

## Quick Start
### Installation
(extremely simple)
```bash
git clone https://github.com/JesseZZZZZ/RepoZero.git
cd RepoZero
pip install -r requirements.txt
```

### Download Dataset

**Option 1 (Recommended): Download via script from HuggingFace**
```bash
python download_data.py
```

**Option 2: Manual download from Google Drive**
- [RepoZero-Py2JS](https://drive.google.com/file/d/1j90jH-YSu3J8IqsW7v79P95W4SgPoGrU/view?usp=drive_link) → Place as `./repozero_py2js.zip`
- [RepoZero-C2Rust](https://drive.google.com/file/d/10sBJG5NLGPR1anLEieI4WYenyXLVmEX7/view?usp=sharing) → Place as `./repozero_c2rust.zip`
### Prerequisites

```bash
# Docker (latest)
docker --version

# Python 3.9+
python --version

# OpenAI-compatible API credentials
# You can replace it with your own url and key
export BASE_URL="https://openrouter.ai/api/v1/"
export API_KEY="your-api-key-here"

# Only needed if you downloaded manually (Option 2)
# Skip this if you used download_data.py (Option 1)
unzip repozero_py2js.zip
unzip repozero_c2rust.zip
```

### Expected Directory Structure

After downloading and extracting, your RepoZero directory should look like this:

```
RepoZero/
├── crossant.json                  # Croissant metadata descriptor
├── LICENSE                        # CC0 1.0 license
├── README.md                      # Main documentation (Docker implementation)
├── README_LOCAL.md                # Local (non-Docker) implementation guide
├── release.sh                     # Release script
├── requirements.txt               # Python dependencies
│
├── C2Rust/                        # C++ to Rust benchmark
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
│   ├── api_lines.jsonl            # API line counts
│   ├── cleaned_test_cases.jsonl   # Test case parameters for evaluation
│   └── recompile_all.sh           # Script to recompile C++ executables
│
├── Py2JS/                         # Python to JavaScript benchmark
│   └── dataset/                   # Python source files (24 libraries, 20 test files each)
│       ├── base58/  bech32/  bencoder/  bidict/  bitarray/  bitstring/
│       ├── boltons/  canonicaljson/  construct/  deepdiff/  ecdsa/
│       ├── fractions/  furl/  idna/  jose/  jsonschema/  markdown/
│       ├── moneyed/  mpmath/  networkx/  pbkdf2/  pyaes/  rsa/
│       ├── rlp/  schedule/  sqlparse/  whoosh/  yaml/
│       └── testcases_60/          # Test case parameter JSONL files
│
├── evaluate/                      # Evaluation scripts
│   ├── eval_c2rust.py             # C2Rust evaluation
│   ├── eval_c2rust_mini.py        # C2Rust mini-swe-agent evaluation
│   ├── eval_py2js.py              # Py2JS evaluation
│   ├── eval_py2js_docker.py       # Py2JS Docker evaluation
│   ├── eval_py2js_mini.py         # Py2JS mini-swe-agent evaluation
│   └── calculate_all_pass.py      # Detailed statistics with Bootstrap CI
│
├── run_c2rust/                    # Local C2Rust implementation
│   ├── run_all_openai.py
│   ├── run_all_anthropic.py
│   ├── run_mini_swe_agent_anthropic.py
│   ├── run_terminal_agent_4_openai.py
│   └── run_terminal_agent_4_anthropic.py
│
├── run_c2rust_docker/            # 🐳 Docker-based C2Rust implementation
│   ├── Dockerfile                 # Docker image build file
│   ├── libstdc++.so.6.0.30        # libstdc++ for compatibility
│   ├── README.md                  # Docker documentation
│   ├── compile_cpp_tests.sh       # Compile C++ tests script
│   ├── run_all_docker.py          # Main Docker evaluation script
│   └── run_terminal_agent.py      # Docker terminal agent core
│
├── run_py2js/                    # Local Py2JS implementation
│   ├── run_all_openai.py
│   ├── run_all_anthropic.py
│   ├── run_all_loop_openai.py
│   ├── run_all_loop_mini_openai.py
│   ├── run_terminal_agent_openai.py
│   └── run_terminal_agent_anthropic.py
│
└── run_py2js_docker/            # 🐳 Docker-based Py2JS implementation
    ├── README.md                  # Docker documentation
    ├── run_all_docker.py          # Main Docker evaluation script
    └── run_terminal_agent.py      # Docker terminal agent core
```

---

## C2Rust Docker Implementation
By default, the Docker image for C2Rust evaluation is ```ghcr.io/jessezzzzz/c2rust-arena:latest```, you do NOT need to change it, and the code can run directly.
### Quick Start

```bash
cd run_c2rust_docker

# Run with default settings
python run_all_docker.py

# Custom number of processes (concurrent evaluations)
python run_all_docker.py -k 8

# Custom model
export MODEL_NAME="deepseek-v3.1-250821"
python run_all_docker.py

# Custom Docker image
export REPOZERO_DOCKER_IMAGE="your-custom-image:latest"
python run_all_docker.py
```
---

## Py2JS Docker Implementation
By default, the Docker image for Py2JS evaluation is ```ghcr.io/jessezzzzz/py2js-arena:latest```, you do NOT need to change it, and the code can run directly.
### Quick Start

```bash
cd run_py2js_docker

# Run with default settings (4 concurrent processes)
python run_all_docker.py

# Custom number of processes
python run_all_docker.py -k 8

# Custom model
export MODEL_NAME="deepseek-v3.1-250821"
python run_all_docker.py

# Custom Docker image
export REPOZERO_DOCKER_IMAGE="my-custom-image:latest"
python run_all_docker.py
```

### Docker Environment

Each task runs in an isolated container with:

- **Workspace**: `/workspace`
- **Dataset**: `/workspace/dataset` (source files + executables)
- **Output**: `/output` (generated JavaScript or Rust files)
- **Node.js**: Available for running generated code
- **Network**: Disabled (`--network none`) for security

### Docker Implementation Details

- **Isolation**: Network-disabled containers for security
- **File Handling**: Source files and pre-compiled executables are copied into containers
- **Output**: Generated JavaScript files are copied back to host after processing

---

## Local Implementation

For local (non-Docker) evaluation, see [README_LOCAL.md](README_LOCAL.md).

---

## About RepoZero

**RepoZero** is a benchmark dataset and evaluation suite for assessing the ability of large language models to perform *zero-shot repository-level code translation* — migrating entire real-world library codebases across programming language ecosystems.

### Benchmark Coverage

| Task | Source | Target | Libraries | Test Files |
|------|--------|--------|-----------|------------|
| **C2Rust** | C++ | Rust | 11 | 200 |
| **Py2JS** | Python | JavaScript (Node.js ESM) | 24 | 400 |

**Total benchmark**: 600 test files across 35 open-source libraries.

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

## Dataset Format

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
