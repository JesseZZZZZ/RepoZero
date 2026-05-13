# Py2JS Docker Implementation

This directory contains the Docker-based implementation for running Py2JS (Python to JavaScript) translation evaluations in isolated containers.

## Quick Start

```bash
# Install dependencies
pip install openai

# Set up environment variables
export BASE_URL="https://openrouter.ai/api/v1/"
export API_KEY="your-api-key-here"
export MODEL_NAME="deepseek-v3.2"  # optional

# Run evaluation
python run_all_docker.py

# Or with custom settings
python run_all_docker.py -k 8 -m deepseek-v3.1-250821
```

## Files

| File | Description |
|------|-------------|
| `run_all_docker.py` | Main evaluation script that orchestrates Docker containers for concurrent processing |
| `run_terminal_agent.py` | Core terminal agent that executes commands inside Docker containers |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | OpenAI-compatible API base URL | `https://openrouter.ai/api/v1` |
| `API_KEY` | API key for OpenAI-compatible endpoint | — (required) |
| `MODEL_NAME` | Model name to use | `deepseek-v3.2` |
| `REPOZERO_DOCKER_IMAGE` | Docker image to use | `ghcr.io/jessezzzzz/repoarena-new:latest` |

### Command Line Arguments

```bash
python run_all_docker.py [-h] [-k NUM_PROCESSES] [-m MODEL]
```

- `-k, --num-processes`: Number of concurrent Docker containers (default: 4)
- `-m, --model`: Model name to use (overrides MODEL_NAME env var)

## How It Works

1. **Pull Docker Image**: The script pulls the pre-built Docker image `ghcr.io/jessezzzzz/repoarena-new:latest` containing Python test executables

2. **Create Container per Task**: For each Python source file, a temporary Docker container is created with:
   - Network isolation (`--network none`)
   - Source file copied to `/workspace/dataset/`
   - Pre-compiled executable copied to `/workspace/dataset/`
   - Output directory at `/output/`

3. **Run Agent**: The terminal agent executes commands inside the container to:
   - Read and analyze the Python source code
   - Run the pre-compiled executable to observe behavior
   - Generate equivalent JavaScript (`.mjs`) code
   - Save output to `/output/`

4. **Copy Results**: Generated files are copied from `/output/` to the host system

5. **Cleanup**: Container is removed after processing

## Container Environment

| Path | Purpose |
|------|---------|
| `/workspace` | Working directory |
| `/workspace/dataset/` | Source files and executables |
| `/output/` | Generated JavaScript output |
| `/bin/sh` | Shell for command execution |
| `node` | Node.js runtime for testing generated code |

## Example Usage

```bash
# Run with 8 concurrent processes
python run_all_docker.py -k 8

# Run with specific model
python run_all_docker.py -m gpt-4o

# Run with custom Docker image (must contain same dataset structure)
export REPOZERO_DOCKER_IMAGE="my-custom-image:latest"
python run_all_docker.py
```

## Output

Generated files are written to:
```
Py2JS/output/<MODEL_NAME>/packages/
├── base58_test1_pkg/
│   ├── utils.mjs
│   └── test1.mjs
├── base58_test2_pkg/
│   └── test2.mjs
└── ...
```

## Troubleshooting

### Docker Image Pull Failed

```bash
# Manually pull the image
docker pull ghcr.io/jessezzzzz/repoarena-new:latest

# Verify it exists
docker images | grep repoarena-new
```

### Container Creation Failed

```bash
# Check Docker is running
docker ps

# Check for existing containers
docker ps -a | grep repoarena

# Clean up stuck containers
docker rm -f $(docker ps -a -q --filter "name=repoarena")
```

### API Errors

```bash
# Verify API credentials
echo $BASE_URL
echo $API_KEY

# Test API connection
curl -X POST "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v3.2","messages":[{"role":"user","content":"test"}]}'
```

## Security

- **Network Isolation**: Containers run with `--network none` to prevent external access
- **External Package Blocking**: The agent blocks imports from external npm packages
- **Temporary Containers**: Each task uses a fresh container that is deleted after completion
- **Filesystem Limits**: Agent can only access specified directories within the container

## Building Custom Docker Image

To build your own Docker image with the same structure:

```dockerfile
FROM node:18-bullseye

# Set up workspace
WORKDIR /workspace

# Copy dataset (with executables)
COPY dataset /workspace/dataset

# Create output directory
RUN mkdir -p /output

# Keep container alive
CMD tail -f /dev/null
```

Build and push:
```bash
docker build -t your-username/repoarena:latest .
docker push your-username/repoarena:latest
```

Then use:
```bash
export REPOZERO_DOCKER_IMAGE="your-username/repoarena:latest"
python run_all_docker.py
```
