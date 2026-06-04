import os
import subprocess
import json
import re
import argparse
from pathlib import Path
from openai import OpenAI

# --- Configuration ---
BASE_URL = os.getenv("BASE_URL", "https://qianfan.baidubce.com/v2/")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-v3.2")

if not API_KEY:
    raise ValueError("API_KEY environment variable must be set")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

SYSTEM_PROMPT = """You are an AI expert with Linux terminal access inside a Docker container. You can execute commands inside the container to complete tasks.

When you need to execute a command, use this exact format:
<tool_call>
command content here
</tool_call>

Important rules:
- Execute only one command at a time
- Wait for command results before deciding next steps
- When the task is complete, give a final summary WITHOUT any <tool_call> tags
- All operations are performed in an isolated container environment
"""


def call_api(messages, model=MODEL_NAME):
    """Call qianfan-compatible API"""
    clean_messages = []
    for msg in messages:
        clean_messages.append({"role": msg["role"], "content": str(msg.get("content") or "")})

    try:
        response = client.chat.completions.create(model=model, messages=clean_messages)
        return response.model_dump()
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
        return None


def parse_tool_call(content):
    """Parse tool_call from model output"""
    match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


class DockerTerminalAgent:
    """Terminal Agent that executes commands inside Docker containers"""

    def __init__(self, container_name, working_dir=None):
        """
        Initialize Docker container terminal Agent

        Args:
            container_name: Docker container name or ID
            working_dir: Working directory inside container, defaults to container default
        """
        self.container_name = container_name
        self.working_dir = working_dir
        self._validate_container()

    def _validate_container(self):
        """Validate that container exists and is running"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format={{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Container '{self.container_name}' does not exist or is inaccessible")
            if result.stdout.strip() != "true":
                raise RuntimeError(f"Container '{self.container_name}' is not running")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Container status check timeout, ensure Docker service is running")
        except FileNotFoundError:
            raise RuntimeError("Docker command not found, ensure Docker is installed")

    def execute_shell(self, command):
        """
        Execute shell command inside Docker container

        Args:
            command: Command to execute

        Returns:
            String result of command execution
        """
        print(f"\n[Executing container command]: {command}")

        # Security patterns to block external npm package imports
        forbidden_patterns = [
            r"require\s*\(\s*['\"](?![./]).*?['\"]\s*\)",
            r"import\s+.*?from\s+['\"](?![./]).*?['\"]",
            r"import\s*\(\s*['\"](?![./]).*?['\"]\s*\)",
            r"import\s+['\"](?![./]).*?['\"]"
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, command):
                error_msg = "SECURITY RESTRICTION: External NPM package imports are not allowed. Only relative paths (./) or absolute paths (/) may be used for local file references."
                print(f"\n{error_msg}")
                return error_msg

        docker_cmd = ["docker", "exec"]
        if self.working_dir:
            docker_cmd.extend(["-w", self.working_dir])
        docker_cmd.extend([self.container_name, "/bin/sh", "-c", command])

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command execution timeout (60s)"
        except Exception as e:
            return f"Error: {str(e)}"


def run_reasoning_agent(user_query, container_name, working_dir=None, model_name=None, max_turns=12):
    """Run reasoning Agent inside Docker container"""
    docker_agent = DockerTerminalAgent(container_name, working_dir)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    total_input_tokens = 0
    total_output_tokens = 0

    for turn_index in range(max_turns):
        response = call_api(messages, model=model_name)

        if not response or "choices" not in response:
            print("[ERROR] API call failed or returned invalid format")
            break

        if "usage" in response:
            usage = response["usage"]
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)

        msg = response["choices"][0]["message"]
        content = msg.get("content", "") or ""

        if msg.get("reasoning_details"):
            print(f"\n[Model reasoning...]:\n--- Reasoning ---\n{msg['reasoning_details']}\n-----------------")

        messages.append({"role": "assistant", "content": content})

        command = parse_tool_call(content)
        if not command:
            print(f"\n[Final result]:\n{content}")
            break

        observation = docker_agent.execute_shell(command)
        print("[Tool execution result]:\n", observation[:1000])

        messages.append({"role": "user", "content": f"<tool_result>\n{observation}\n</tool_result>"})

    else:
        print(f"\n[Final result]:\nStopped after reaching max_turns={max_turns}.")

    return {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal Agent running inside Docker container")
    parser.add_argument("--container", required=True, help="Docker container name or ID")
    parser.add_argument("--work-dir", help="Working directory inside container (optional)")
    args = parser.parse_args()

    task = input("Enter task you want Agent to execute: ")
    run_reasoning_agent(
        task,
        container_name=args.container,
        working_dir=args.work_dir,
        model_name=MODEL_NAME
    )
