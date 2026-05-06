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


def check_cargo_toml_dependencies(cargo_toml_path):
    """Strip any [dependencies] entries from Cargo.toml and return an error message if found."""
    if not cargo_toml_path or not os.path.exists(cargo_toml_path):
        return None

    try:
        with open(cargo_toml_path, "r", encoding="utf-8") as f:
            content = f.read()

        if re.search(r"^\s*\[dependencies\]", content, re.MULTILINE):
            dep_match = re.search(
                r"^\s*\[dependencies\](.*?)(?=^\s*\[|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if dep_match:
                dep_section = re.sub(r"#.*$", "", dep_match.group(1), flags=re.MULTILINE)
                if re.search(r'^\s*\w+\s*=\s*["\']', dep_section, re.MULTILINE):
                    new_content = re.sub(
                        r"^\s*\[dependencies\].*?(?=^\s*\[|\Z)",
                        "[dependencies]",
                        content,
                        flags=re.MULTILINE | re.DOTALL,
                    )
                    with open(cargo_toml_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return "External dependencies are not allowed. Use only the Rust standard library (std)."

    except Exception as e:
        print(f"Error checking Cargo.toml: {e}")

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


def run_reasoning_agent(user_query, model_name=None, max_total_tokens=2560000, cargo_toml_path=None):
    """
    Run an agentic loop using the Qianfan API.

    Returns a dict with token counts, or an error dict if the token limit is reached.
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

        current_total = total_input_tokens + total_output_tokens
        if current_total >= max_total_tokens:
            print(f"\nToken limit reached: {current_total}/{max_total_tokens}")
            return {
                "error": f"Token limit reached ({max_total_tokens}), task terminated.",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": current_total,
            }

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

            dependency_error = check_cargo_toml_dependencies(cargo_toml_path)
            if dependency_error:
                observation = f"{observation}\n\n{dependency_error}"

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
