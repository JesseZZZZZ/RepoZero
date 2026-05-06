import os
import subprocess
import json
import re
from openai import OpenAI

API_URL = os.environ.get("QIANFAN_API_URL", "https://qianfan.baidubce.com/v2/")
API_KEY = os.environ.get("QIANFAN_API_KEY", "")

client = OpenAI(base_url=API_URL, api_key=API_KEY)


def call_qianfan_api(messages, tools=None, model="deepseek-v3.1-250821"):
    params = {"model": model, "messages": messages}
    if tools:
        params["tools"] = tools
    try:
        response = client.chat.completions.create(**params)
        return response.model_dump()
    except Exception as e:
        print(f"API call failed: {e}")
        return None


def execute_shell(command):
    """Execute a shell command. Blocks forbidden external NPM package patterns."""
    print(f"\n[shell] {command}")

    forbidden_patterns = [
        # require("pkg") where pkg does not start with . or /
        r"require\s*\(\s*['\"](?![./]).*?['\"]\s*\)",
        # import ... from "pkg" where pkg does not start with . or /
        r"import\s+.*?from\s+['\"](?![./]).*?['\"]",
        # dynamic import("pkg")
        r"import\s*\(\s*['\"](?![./]).*?['\"]\s*\)",
        # bare import "pkg"
        r"import\s+['\"](?![./]).*?['\"]",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, command):
            error_msg = "Blocked: loading external NPM packages is not allowed. Use only relative (./) or absolute (/) local file paths."
            print(error_msg)
            return error_msg

    env = os.environ.copy()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a Linux shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The full shell command to run."}
                },
                "required": ["command"],
            },
        },
    }
]


def run_reasoning_agent(user_query, model_name=None):
    """
    Run an agentic loop using the Qianfan (OpenAI-compatible) API.

    Returns a dict with token counts.
    """
    messages = [
        {"role": "system", "content": "You are an AI expert with Linux terminal access. Use your reasoning ability before calling any tools."},
        {"role": "user", "content": user_query},
    ]

    total_input_tokens = 0
    total_output_tokens = 0

    while True:
        response = call_qianfan_api(messages, tools=tools, model=model_name)

        if not response or "choices" not in response:
            print("API call failed or returned unexpected format.")
            break

        if "usage" in response:
            usage = response["usage"]
            total_input_tokens  += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)

        choice = response["choices"][0]
        msg = choice["message"]

        if "reasoning_details" in msg and msg["reasoning_details"]:
            print(f"\n[reasoning]\n{msg['reasoning_details']}")

        msg_to_append = {"role": "assistant", "content": msg.get("content", "")}
        if "reasoning_details" in msg:
            msg_to_append["reasoning_details"] = msg["reasoning_details"]
        if "tool_calls" in msg and msg["tool_calls"]:
            msg_to_append["tool_calls"] = msg["tool_calls"]

        messages.append(msg_to_append)

        if "tool_calls" not in msg or not msg["tool_calls"]:
            print(f"\n[final answer]\n{msg.get('content', '')}")
            break

        for tool_call in msg["tool_calls"]:
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError as e:
                error_msg = f"Invalid tool arguments: {e}\nRaw: {tool_call['function']['arguments']}\nPlease fix the argument format and retry."
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": "execute_shell",
                    "content": error_msg,
                })
                print(f"[tool result]\n{error_msg[:1000]}")
                continue

            observation = execute_shell(args["command"])
            print(f"[tool result]\n{observation[:1000]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": "execute_shell",
                "content": observation,
            })

    return {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
    }


if __name__ == "__main__":
    task = input("Enter task for the agent: ")
    run_reasoning_agent(task, model_name="deepseek-v3.2")
