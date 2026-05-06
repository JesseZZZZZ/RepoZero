import os
import subprocess
import json
import re
import anthropic

BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

MAX_TOOL_CALLS = 270


def call_anthropic_api(messages, tools=None, model=None):
    """Call the Anthropic Messages API, converting from OpenAI-style message format."""
    client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "tool":
            continue
        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

    anthropic_tools = []
    if tools:
        for tool in tools:
            if tool["type"] == "function":
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"],
                })

    try:
        kwargs = {"model": model, "max_tokens": 40960, "messages": anthropic_messages}
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        return client.messages.create(**kwargs)
    except Exception as e:
        print(f"API call failed: {e}")
        return None


def execute_shell(command):
    """Execute a shell command. Blocks forbidden Rust dependency patterns."""
    print(f"\n[shell] {command}")

    forbidden_patterns = [
        r"cargo\s+add\s+\S+",
        r"cargo\s+install\s+\S+",
        r"(echo|printf).*['\"]\s*\w+\s*=\s*['\"][\d\.\w-]+['\"].*\>>?.*Cargo\.toml",
        r"(echo|printf).*\b(\w+)\s*=\s*[\"\']\d[\d\.\w-]*[\"\'].*>>?.*Cargo\.toml",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            error_msg = "Blocked: installing or using external Rust crates is not allowed. Use only std and local files."
            print(error_msg)
            return error_msg

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            env=os.environ.copy(),
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
    Run an agentic loop using the Anthropic API.

    Returns a dict with token counts and the full message history.
    """
    messages = [
        {"role": "user", "content": "You are an AI expert with Linux terminal access. Use your reasoning ability before calling any tools."},
        {"role": "user", "content": user_query},
    ]

    total_input_tokens = 0
    total_output_tokens = 0
    tool_call_count = 0

    while True:
        if tool_call_count >= MAX_TOOL_CALLS:
            print(f"\n[warning] Max tool calls reached ({MAX_TOOL_CALLS}). Stopping.")
            break

        response = call_anthropic_api(messages, tools=tools, model=model_name)

        if not response or not hasattr(response, "content"):
            print("API call failed or returned unexpected format.")
            break

        if hasattr(response, "usage"):
            total_input_tokens  += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        assistant_message = {"role": "assistant", "content": []}
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                print(f"\n[reply]\n{block.text}")
                assistant_message["content"].append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
                assistant_message["content"].append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        messages.append(assistant_message)

        if not tool_calls:
            break

        for tool_call in tool_calls:
            tool_call_count += 1
            print(f"\n[tool call {tool_call_count}/{MAX_TOOL_CALLS}]")

            if tool_call["name"] == "execute_shell":
                try:
                    command = tool_call["input"].get("command")
                    if not command:
                        raise ValueError("Missing 'command' field in tool input.")

                    observation = execute_shell(command)
                    print(f"[tool result]\n{observation[:1000]}")

                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_call["id"], "content": observation}],
                    })
                except (KeyError, ValueError, AttributeError) as e:
                    print(f"Tool call error: {e}\nInput: {tool_call['input']}")
                    return {
                        "error": f"Invalid tool arguments: {e}",
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": total_input_tokens + total_output_tokens,
                    }

    return {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "messages": messages,
    }


if __name__ == "__main__":
    task = input("Enter task for the agent: ")
    run_reasoning_agent(task, model_name="claude-sonnet-4-6")
