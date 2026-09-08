import json
import re
import os
import traceback
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS

from dotenv import load_dotenv
load_dotenv()

# ── Setup OpenAI-compatible client configuration ──────────────────────────
api_key = os.getenv("OPENAI_API_KEY", "").strip()
base_url = os.getenv("OPENAI_BASE_URL", "").strip()
model_name = os.getenv("MODEL_NAME", "").strip()

client = None
MODEL_NAME = "unknown"

if not api_key and not base_url:
    print("[llm_engine] WARNING: Neither OPENAI_API_KEY nor OPENAI_BASE_URL is set. Chat will fail until configured.")
else:
    client_kwargs = {"timeout": 60.0}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    MODEL_NAME = model_name or ("gpt-4o-mini" if not base_url or "openai" in base_url else "auto")

MAX_TOOL_ROUNDS = 5
MAX_MSG_CHARS = 15000

SYSTEM_PROMPT = """
You are "TNEA GPT", the official Admissions AI Counselor for Tamil Nadu Engineering Admissions.

STRICT MANDATES:
1. THE GREETING RULE: If the user inputs a simple greeting, reply with exactly ONE short sentence. Do NOT introduce your full name or capabilities unless asked.
2. FORMAL & CONCISE: Use formal, professional English. Keep responses extremely simple and brief.
3. DATA & TOOLS:
   - When asked for cutoffs, closing ranks, or eligibility, query the tools (`get_college_cutoffs`, `get_historical_cutoffs`, `predict_colleges`, `search_colleges`, `get_seat_matrix`).
   - If a user asks for 5-year cutoff trends or historical comparisons (2021-2025), use `get_historical_cutoffs`.
   - If a user asks about top/best colleges in Tamil Nadu, you MUST call `get_top_colleges` first. NEVER invent or guess college names, TNEA codes, or rankings.
   - Never fabricate or guess cutoffs, ranks, or college codes. Rely strictly on tool outputs.
4. STRUCTURE: Output clear, well-formatted markdown text/tables. Limit tables to top matches or the requested branches/categories. Output your response exactly ONCE.
"""


def _truncate_messages(messages: list) -> list:
    """Ensure no single message exceeds the character limit."""
    safe = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > MAX_MSG_CHARS:
            msg = {**msg, "content": content[:MAX_MSG_CHARS] + "\n...[truncated]"}
        safe.append(msg)
    return safe


def _sse(event: dict) -> str:
    """Format a server-sent event payload."""
    return f"data: {json.dumps(event)}\n\n"


def stream_chat(user_message: str, history: list):
    # ── Guard: client not configured ──────────────────────────────────────
    if client is None:
        yield _sse({"type": "error", "content": "Chat service is not configured. Please set OPENAI_API_KEY or OPENAI_BASE_URL in your .env file."})
        return

    messages = _truncate_messages(
        [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_message}]
    )

    try:
        final_content = None

        for _round in range(MAX_TOOL_ROUNDS):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME, messages=messages,
                    tools=TOOLS_SCHEMA, tool_choice="auto"
                )
            except RateLimitError:
                yield _sse({"type": "error", "content": "Rate limit reached. Please wait a moment and try again."})
                return
            except APITimeoutError:
                yield _sse({"type": "error", "content": "The AI service timed out. Please try again."})
                return
            except APIConnectionError:
                yield _sse({"type": "error", "content": "Could not connect to the AI service. Please check your network."})
                return
            except APIError as api_err:
                yield _sse({"type": "error", "content": f"AI service error: {api_err}"})
                return

            if not response or not response.choices:
                yield _sse({"type": "error", "content": "The AI returned an empty response. Please try again."})
                return

            msg = response.choices[0].message
            if msg is None:
                yield _sse({"type": "error", "content": "The AI returned an empty message. Please try again."})
                return

            if msg.tool_calls:
                assistant_msg = {"role": "assistant", "content": msg.content or ""}
                assistant_msg["tool_calls"] = [
                    {
                        "id": t.id, "type": "function",
                        "function": {"name": t.function.name, "arguments": t.function.arguments or "{}"}
                    } for t in msg.tool_calls
                ]
                messages.append(assistant_msg)

                for tool in msg.tool_calls:
                    fn_name = tool.function.name or ""
                    fn_args_str = tool.function.arguments or "{}"
                    yield _sse({"type": "thought", "content": f"Searching database via {fn_name}..."})

                    try:
                        fn_args = json.loads(fn_args_str)
                    except (json.JSONDecodeError, TypeError):
                        fn_args = {}

                    tool_fn = AVAILABLE_TOOLS.get(fn_name)
                    if tool_fn is None:
                        output = json.dumps({"error": f"Tool '{fn_name}' is not available."})
                        messages.append({"role": "tool", "tool_call_id": tool.id, "name": fn_name, "content": output})
                        continue

                    # Coerce cutoff to float safely
                    if "cutoff" in fn_args:
                        try:
                            fn_args["cutoff"] = float(fn_args["cutoff"])
                        except (ValueError, TypeError):
                            fn_args["cutoff"] = 150.0

                    # Coerce college_code to int safely
                    if "college_code" in fn_args:
                        try:
                            fn_args["college_code"] = int(fn_args["college_code"])
                        except (ValueError, TypeError):
                            fn_args["college_code"] = 0

                    # Guard empty required string args
                    for key in ("college_code_or_name", "district_or_city", "query"):
                        if key in fn_args:
                            val = fn_args[key]
                            if not isinstance(val, str) or not val.strip():
                                fn_args[key] = "all"

                    try:
                        output = tool_fn(**fn_args)
                    except TypeError as te:
                        output = json.dumps({"error": f"Tool '{fn_name}' call failed: {str(te)}"})
                    except Exception as tool_err:
                        output = json.dumps({"error": f"Tool execution failed: {str(tool_err)}"})

                    messages.append({"role": "tool", "tool_call_id": tool.id, "name": fn_name, "content": output})
                continue
            else:
                final_content = msg.content
                break

        yield _sse({"type": "thought_done"})

        if final_content:
            chunk_size = 4
            words = final_content.split(' ')
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += ' '
                yield _sse({"type": "token", "content": chunk})
        else:
            # AI used all tool rounds without producing text — force one last streaming call
            try:
                stream = client.chat.completions.create(model=MODEL_NAME, messages=messages, stream=True)
                for chunk in stream:
                    if (chunk.choices and chunk.choices[0].delta
                            and chunk.choices[0].delta.content):
                        text = chunk.choices[0].delta.content
                        yield _sse({"type": "token", "content": text})
            except Exception as stream_err:
                yield _sse({"type": "error", "content": f"Failed to generate response: {str(stream_err)}"})

        # Signal end of stream
        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[llm_engine] Unexpected error: {traceback.format_exc()}")
        yield _sse({"type": "error", "content": "An unexpected error occurred. Please try again."})