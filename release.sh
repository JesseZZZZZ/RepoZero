#!/bin/bash

# RepoZero Release Script
# This script helps prepare and publish RepoZero to GitHub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RepoZero GitHub Release Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: This script must be run from the root of a git repository${NC}"
    exit 1
fi

# Step 1: Create a release tag
echo -e "${YELLOW}[Step 1/4]${NC} Creating release tag..."
CURRENT_DATE=$(date +%Y%m%d)
TAG_NAME="v1.0.0-${CURRENT_DATE}"

# Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo -e "${YELLOW}  Tag $TAG_NAME already exists${NC}"
    read -p "Create a new tag name: " -i TAG_NAME
    TAG_NAME=$REPLY
fi

# Create and push the tag
git tag -a "$TAG_NAME" -m "Release v1.0.0 for $CURRENT_DATE"
git push origin "$TAG_NAME"

echo -e "${GREEN}✓${NC} Tag $TAG_NAME created and pushed"
echo ""

# Step 2: Create a GitHub release
echo -e "${YELLOW}[Step 2/4]${NC} Creating GitHub release..."

# Check if gh CLI is installed
if ! command -v gh >/dev/null 2>&1; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Create GitHub release with auto-generated release notes
RELEASE_NOTES="RepoZero v1.0.0 Release - $CURRENT_DATE

## What's New

### 🐳 Docker-Based Py2JS Implementation
- Isolated, reproducible evaluation environment using Docker containers
- Pre-built Docker image: \`ghcr.io/jessezzzzz/repoarena-new:latest\`
- Network isolation for security
- Support for concurrent evaluation with configurable process count

### Enhanced Evaluation Tools
- **eval_py2js_docker.py**: Evaluate Docker-based Py2JS translation results
- **calculate_all_pass.py**: Calculate detailed statistics with Bootstrap CI
  - Per-class pass rates
  - Category-level breakdown (Serialization & Data Formats, Cryptography & Encoding, etc.)
  - Micro/Macro metrics with 95% confidence intervals

### API Configuration
- Default: OpenRouter (https://openrouter.ai/api/v1/)
- Environment variables: \`BASE_URL\` and \`API_KEY\`

### Documentation Updates
- Comprehensive README with Docker implementation details
- Updated environment variable naming (BASE_URL, API_KEY instead of QIANFAN_*)
- All prompts and messages translated to English

## Installation

\`\`\`bash
# Clone the repository
git clone https://github.com/JesseZZZZZ/RepoZero.git
cd RepoZero

# Install dependencies
pip install openai anthropic

# Optional: Install numpy for bootstrap CI
pip install numpy
\`\`\`

## Quick Start

### Docker Evaluation

\`\`\`bash
cd run_py2js_docker
python run_all_docker.py
\`\`\`

### Calculate Statistics

\`\`\`bash
python evaluate/calculate_all_pass.py -m deepseek-v3.2
\`\`\`

---

## Benchmark Overview

- **600 test files** across **35 open-source libraries**
- **24 Python libraries** for Py2JS (400 test files)
- **11 C++ libraries** for C2Rust (200 test files)
- Category-based library classification for detailed analysis

## Links

- [Repository](https://github.com/JesseZZZZZ/RepoZero)
- [Docker Image](https://ghcr.io/jessezzzzz/repoarena-new)
- [Issues](https://github.com/JesseZZZZZ/RepoZero/issues)
"

# Create the release using gh CLI
gh release create "$TAG_NAME" \
    --repo "JesseZZZZZ/RepoZero" \
    --title "RepoZero v1.0.0 - $CURRENT_DATE" \
    --notes "$RELEASE_NOTES"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Release created successfully!"
    echo ""
    echo -e "${GREEN}Release URL:${NC} https://github.com/JesseZZZZZ/RepoZero/releases/tag/$TAG_NAME"
else
    echo -e "${RED}✗${NC} Failed to create release"
    exit 1
fi

echo ""
echo -e "${YELLOW}[Optional]${NC} Create source tarball for archiving..."
git archive --prefix="repozero-$CURRENT_DATE/" HEAD

echo -e "${GREEN}✓${NC} Done!"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Release preparation complete!${NC}"
echo -e "${GREEN}========================================${NC}"
