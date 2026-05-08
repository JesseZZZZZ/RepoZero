# RepoZero

‼️Docker implementation will be released soon, this is a simplified implementation that runs locally.

**❗️Update 20260508** If you want to use this repository to simulate the performance of docker, you can set up an account that has limited access to the file system (read-only for the source repository, and invisible for test cases)

**RepoZero** is a benchmark dataset and evaluation suite for assessing the ability of large language models to perform *zero-shot repository-level code translation* — migrating entire real-world library codebases across programming language ecosystems.

RepoZero covers two translation tasks:

| Task | Source | Target | Libraries | Test Files |
|------|--------|--------|-----------|------------|
| **C2Rust** | C++ | Rust | 11 | 200 |
| **Py2JS** | Python | JavaScript (Node.js ESM) | 24 | 400 |

Total benchmark: **600 test files** across **35 open-source libraries**.

---
## Clone the Codebase and download the raw data
```bash
git clone https://github.com/JesseZZZZZ/RepoZero.git
```
‼️Mannualy Download the raw data via [this link](https://disk.pku.edu.cn/link/AA0A7B7864999C4F84A0FCDF1C2C0A57BF)
Place it under the root of the codebase, the final codebase should be like this: ⬇️
## Repository Structure

```
RepoZero/
├── gold_test_files.jsonl          # Master index of all 600 benchmark test files
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
│   │   └── difficulty.json        # Per-file difficulty classification (EASY/MEDIUM/HARD)
│   └── testcases_60/              # Test case parameter JSONL files (28 libraries)
│
├── evaluate/
│   ├── eval_c2rust.py             # Evaluate C2Rust (terminal-agent output)
│   ├── eval_c2rust_mini.py        # Evaluate C2Rust (mini-swe-agent output)
│   ├── eval_py2js.py              # Evaluate Py2JS (terminal-agent output)
│   └── eval_py2js_mini.py        # Evaluate Py2JS (mini-swe-agent output)
│
├── run_c2rust/
│   ├── run_all_openai.py          # Run C2Rust with OpenAI-compatible API (terminal agent)
│   ├── run_all_anthropic.py       # Run C2Rust with Anthropic API (terminal agent)
│   ├── run_mini_swe_agent_anthropic.py  # Run C2Rust via mini-swe-agent
│   ├── run_terminal_agent_4_openai.py   # Terminal agent core (OpenAI)
│   └── run_terminal_agent_4_anthropic.py # Terminal agent core (Anthropic)
│
└── run_py2js/
    ├── run_all_openai.py          # Run Py2JS with OpenAI-compatible API (terminal agent)
    ├── run_all_anthropic.py       # Run Py2JS with Anthropic API (terminal agent)
    ├── run_all_loop_openai.py     # Run Py2JS with iterative self-repair loop (OpenAI)
    ├── run_all_loop_mini_openai.py # Run Py2JS loop via mini-swe-agent (OpenAI)
    ├── run_mini_swe_agent_anthropic.py  # Run Py2JS via mini-swe-agent (Anthropic)
    ├── run_terminal_agent_openai.py     # Terminal agent core (OpenAI)
    └── run_terminal_agent_anthropic.py  # Terminal agent core (Anthropic)
```

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

**Difficulty tiers:** Each Py2JS test file is classified as EASY (148), MEDIUM (149), or HARD (149) based on translation complexity.

---

## Evaluation Metrics

All evaluation scripts report three metrics:

| Metric | Description |
|--------|-------------|
| **All-Pass Rate** | Fraction of source files where *all* test cases pass |
| **Test-Case Pass Rate** | Mean per-file fraction of passing test cases |
| **API Coverage** | Mean fraction of output lines that match between source and translated code |

---

## Running the Benchmark

### Prerequisites

```bash
# Python 3.9+
pip install anthropic openai

# Node.js 18+ (for Py2JS evaluation)
node --version

# Optional: mini-swe-agent (for mini harness scripts)
pip install mini-swe-agent
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_BASE_URL` | Custom Anthropic API endpoint | Anthropic default |
| `QIANFAN_API_URL` | OpenAI-compatible API base URL | `https://qianfan.baidubce.com/v2` |
| `QIANFAN_API_KEY` | API key for OpenAI-compatible endpoint | — |
| `PYTHON_BIN` | Python interpreter for evaluation | `python3` |
| `NODE_BIN` | Node.js interpreter for evaluation | `node` |
| `MINI_SWE_AGENT_BIN` | mini-swe-agent binary path | `mini` |

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

### Run Py2JS

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

To override the model name, edit the `model_name` variable at the top of the relevant script, or (for scripts that support it) pass `-m <model>` on the command line.

### Evaluate Results

```bash
# Evaluate Py2JS terminal-agent output
python evaluate/eval_py2js.py -m <model_name>

# Evaluate Py2JS mini-swe-agent / loop output
python evaluate/eval_py2js_mini.py -m <model_name>

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

---

## Output Directory Layout

Run scripts write translated files to the following locations:

| Script type | Output path |
|-------------|-------------|
| Terminal agent (Py2JS) | `Py2JS/output/<model_name>/testfiles/` |
| mini-swe-agent (Py2JS) | `Py2JS/output_mini/<model_name>/testfiles/` |
| Loop — terminal agent | `Py2JS/output_loop/<model_name>_retry<N>/testfiles/` |
| Loop — mini-swe-agent | `Py2JS/output_loop_mini/<model_name>_retry<N>/testfiles/` |
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
