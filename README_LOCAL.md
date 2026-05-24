# RepoZero - Local (Non-Docker) Implementation

This document covers running RepoZero evaluations locally without Docker. For the recommended Docker-based implementation, see the main [README.md](../README.md).

## Quick Start

### Prerequisites

```bash
# Python 3.9+
python --version

# Node.js 18+ (for Py2JS evaluation)
node --version

# Optional: numpy for bootstrap CI
pip install numpy
```

### Installation

```bash
# Clone the repository
git clone https://github.com/JesseZZZZZ/RepoZero.git
cd RepoZero

# Create conda environment (optional)
conda create -n repozero python==3.10
conda activate repozero

# Install required packages
pip install anthropic openai requests
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_BASE_URL` | Custom Anthropic API endpoint | Anthropic default |
| `BASE_URL` | OpenAI-compatible API base URL | `https://openrouter.ai/api/v1` |
| `API_KEY` | API key for OpenAI-compatible endpoint | — |
| `MODEL_NAME` | Model name to use | `deepseek-v3.2` |
| `PYTHON_BIN` | Python interpreter for evaluation | `python3` |
| `NODE_BIN` | Node.js interpreter for evaluation | `node` |

## Running the Benchmark

### C2Rust (Local)

```bash
cd run_c2rust

# Terminal agent — OpenAI-compatible API
python run_all_openai.py

# Terminal agent — Anthropic API
python run_all_anthropic.py

# mini-swe-agent harness
python run_mini_swe_agent_anthropic.py
```

### Py2JS (Local)

```bash
cd run_py2js

# Terminal agent — OpenAI-compatible API
python run_all_openai.py

# Terminal agent — Anthropic API
python run_all_anthropic.py

# Iterative self-repair loop (generates test cases, attempts fixes up to N times)
python run_all_loop_openai.py

# Loop mode via mini-swe-agent
python run_all_loop_mini_openai.py
```

To override the model name, edit the `model_name` variable at the top of the relevant script.

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **All-Pass Rate** | Fraction of source files where *all* test cases pass |
| **Test-Case Pass Rate** | Mean per-file fraction of passing test cases |

## Evaluate Results

```bash
# Evaluate Py2JS terminal-agent output
python evaluate/eval_py2js.py -m <model_name>

# Evaluate Py2JS mini-swe-agent / loop output
python evaluate/eval_py2js_mini.py -m <model_name>

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

## Calculate Detailed Statistics

```bash
# Calculate statistics for a specific model
python evaluate/calculate_all_pass.py -m deepseek-v3.2

# Calculate with custom results directory
python evaluate/calculate_all_pass.py --results-dir ./Py2JS/output/results/deepseek-v3.2

# Use fewer bootstrap samples for faster calculation
python evaluate/calculate_all_pass.py -n-bootstrap 100
```

This script provides:
- **Per-class statistics**: Pass rates for each test class (library)
- **Category-level breakdown**: Statistics grouped by library categories
- **Micro/Macro rates**: Both all-pass and test-case-pass rates
- **Bootstrap Confidence Intervals**: 95% CI for both metrics

## Output Directory Layout

| Script type | Output path |
|-------------|-------------|
| Terminal agent (Py2JS) | `Py2JS/output/<model_name>/testfiles/` |
| mini-swe-agent (Py2JS) | `Py2JS/output_mini/<model_name>/testfiles/` |
| Loop — terminal agent | `Py2JS/output_loop/<model_name>_retry<N>/testfiles/` |
| Loop — mini-swe-agent | `Py2JS/output_loop_mini/<model_name>_retry<N>/testfiles/` |
| Terminal agent (C2Rust) | `C2Rust/output/<model_name>/testfiles/` |
| mini-swe-agent (C2Rust) | `C2Rust/output_mini/<model_name>/testfiles/` |

Library helper files are written alongside under a `packages/` subdirectory.

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

## License

Dataset and code are released under [CC0 1.0](https://spdx.org/licenses/CC0-1.0). All source code used in the benchmark is derived from open-source repositories; their original licenses remain in effect within their respective directories.