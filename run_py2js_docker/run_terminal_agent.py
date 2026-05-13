import os
import subprocess
import json
import re
import argparse
from pathlib import Path
from openai import OpenAI

# --- Configuration ---
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1/")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-v3.2")

if not API_KEY:
    raise ValueError("API_KEY environment variable must be set")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def call_api(messages, tools=None, model=MODEL_NAME):
    """Call OpenAI-compatible API"""
    params = {"model": model, "messages": messages}
    if tools:
        params["tools"] = tools

    try:
        response = client.chat.completions.create(**params)
        return response.model_dump()
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
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


tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute Linux shell command inside Docker container and return result",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Complete shell command"}
                },
                "required": ["command"],
            },
        },
    }
]


def run_reasoning_agent(user_query, container_name, working_dir=None, model_name=None):
    """
    Run reasoning Agent inside Docker container

    Args:
        user_query: User query
        container_name: Docker container name or ID
        working_dir: Working directory inside container (optional)
        model_name: Model name to use (optional)

    Returns:
        Token statistics dictionary
    """
    docker_agent = DockerTerminalAgent(container_name, working_dir)

    messages = [
        {
            "role": "system",
            "content": "You are an AI expert with Linux terminal access inside a Docker container. You can execute commands inside the container to complete tasks. Use your reasoning ability to analyze tasks before calling tools. All operations are performed in an isolated container environment and cannot affect the host system."
        },
        {"role": "user", "content": user_query}
    ]

    total_input_tokens = 0
    total_output_tokens = 0

    while True:
        response = call_api(messages, tools=tools, model=model_name)

        if not response or "choices" not in response:
            print("[ERROR] API call failed or returned invalid format")
            break

        if "usage" in response:
            usage = response["usage"]
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)

        choice = response["choices"][0]
        msg = choice["message"]

        if "reasoning_details" in msg and msg["reasoning_details"]:
            print("\n[Model reasoning...]:")
            print(f"--- Reasoning ---\n{msg['reasoning_details']}\n-----------------")

        msg_to_append = {"role": "assistant", "content": msg.get("content", "")}
        if "reasoning_details" in msg:
            msg_to_append["reasoning_details"] = msg["reasoning_details"]
        if "tool_calls" in msg and msg["tool_calls"]:
            msg_to_append["tool_calls"] = msg["tool_calls"]

        messages.append(msg_to_append)

        if "tool_calls" not in msg or not msg["tool_calls"]:
            print(f"\n[Final result]:\n{msg.get('content', '')}")
            break

        for tool_call in msg["tool_calls"]:
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError as e:
                print(f"\n[ERROR] Tool call format error: {e}")
                print(f"Original arguments: {tool_call['function']['arguments']}")
                return {
                    "error": f"Invalid tool call argument format: {e}",
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_input_tokens + total_output_tokens
                }

            observation = docker_agent.execute_shell(args['command'])
            print("[Tool execution result]:\n", observation[:1000])
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": "execute_shell",
                "content": observation
            })

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
