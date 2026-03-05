"""Chat endpoint helpers for agent tool calls and confirmations.

Each function returns a Flask jsonify response or None (caller continues normal flow).
Dependencies are passed as arguments to keep testing simple.
"""

import json
import logging

from flask import jsonify

from agent.tools import AGENT_FUNCTION_MAP, DESTRUCTIVE_ACTIONS
from agent.crud import get_module

logger = logging.getLogger(__name__)


def handle_confirmation(confirm_action, sanitize_input, chat_client, chat_model,
                        openai_client, openai_model):
    """Execute a previously-confirmed destructive action and return a summary response.

    Returns a Flask jsonify response.
    """
    action_type = confirm_action.get("type")
    params = confirm_action.get("params", {})

    if action_type not in DESTRUCTIVE_ACTIONS:
        return jsonify({"error": "Invalid action type"}), 400

    func = AGENT_FUNCTION_MAP.get(action_type)
    if not func:
        return jsonify({"error": "Unknown action"}), 400

    sanitized_params = {
        k: sanitize_input(v) if isinstance(v, str) else v
        for k, v in params.items()
    }
    result = func(**sanitized_params)

    try:
        summary_response = chat_client.chat.completions.create(
            model=chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this module operation result in a friendly, concise way. Use a checkmark for success or X for failure.",
                },
                {"role": "user", "content": json.dumps(result)},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        answer = summary_response.choices[0].message.content
    except Exception as e:
        logger.warning(f"DeepSeek summary failed, falling back to OpenAI: {e}")
        summary_response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this module operation result in a friendly, concise way.",
                },
                {"role": "user", "content": json.dumps(result)},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        answer = summary_response.choices[0].message.content

    return jsonify({
        "answer": answer,
        "sources": [],
        "follow_up_questions": [],
        "action_result": result,
    })


def _llm_call(chat_client, chat_model, openai_client, openai_model, messages, tools=None):
    """Call chat LLM with DeepSeek → OpenAI fallback. Returns the completion."""
    kwargs = dict(messages=messages, max_tokens=3000, temperature=0.4)
    if tools:
        kwargs["tools"] = tools
    try:
        return chat_client.chat.completions.create(model=chat_model, **kwargs)
    except Exception as e:
        if chat_client != openai_client:
            logger.warning(f"Primary LLM failed, falling back to OpenAI: {e}")
            return openai_client.chat.completions.create(model=openai_model, **kwargs)
        raise


def handle_tool_call(response_message, messages, user_question, sanitize_input,
                     chat_client, chat_model, openai_client, openai_model,
                     deepseek_client, collection_count):
    """Process one or more sequential tool calls from the LLM response.

    Loops until the LLM returns plain text (no more tool calls), supporting
    multi-step flows like list_category → add_module in a single turn.

    Returns a Flask jsonify response, or None if no tool call was present.
    """
    from agent.tools import AGENT_TOOLS

    if not response_message.tool_calls:
        return None

    current_message = response_message
    last_function_result = None

    # Loop: keep executing tool calls until LLM stops requesting them
    for _ in range(10):   # max 10 tool calls per turn (safety cap)
        if not current_message.tool_calls:
            break

        tool_call = current_message.tool_calls[0]
        function_name = tool_call.function.name
        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            logger.error(f"Tool call JSON parse failed: {e}")
            return jsonify({"error": "Invalid tool arguments from LLM"}), 400

        logger.info(f"Agent tool call: {function_name}({function_args})")

        # Sanitize string arguments
        for key, val in function_args.items():
            if isinstance(val, str):
                function_args[key] = sanitize_input(val)

        # Destructive action — pause and return pending_action for frontend confirmation
        if function_name in DESTRUCTIVE_ACTIONS:
            current_module = get_module(function_args.get("module_name", ""))

            if function_name == "update_module":
                desc = f"Update module '{function_args.get('module_name', '')}'"
                if current_module.get("found"):
                    desc += f" (current code: {current_module['code']})"
                if function_args.get("new_code"):
                    desc += f" to new code: {function_args['new_code']}"
            elif function_name == "delete_module":
                desc = f"Delete module '{function_args.get('module_name', '')}'"
                if current_module.get("found"):
                    desc += f" (code: {current_module['code']})"
            else:
                desc = f"{function_name}: {function_args}"

            return jsonify({
                "answer": f"This action requires confirmation: {desc}",
                "sources": [],
                "follow_up_questions": [],
                "pending_action": {
                    "type": function_name,
                    "params": function_args,
                    "description": desc,
                },
            })

        # Non-destructive — execute immediately and loop back to LLM
        func = AGENT_FUNCTION_MAP.get(function_name)
        last_function_result = func(**function_args)

        messages.append(current_message.model_dump())
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(last_function_result),
        })

        # Call LLM again with tools still available so it can chain another call
        follow_up_llm = _llm_call(
            chat_client, chat_model, openai_client, openai_model,
            messages, tools=AGENT_TOOLS,
        )
        current_message = follow_up_llm.choices[0].message

    answer = current_message.content or ""

    # Generate follow-up questions for tool results too
    follow_up_questions = []
    try:
        fq_client = deepseek_client or openai_client
        fq_model = chat_model if deepseek_client else "gpt-4o-mini"
        follow_up_response = fq_client.chat.completions.create(
            model=fq_model,
            messages=[
                {
                    "role": "system",
                    "content": "You generate relevant follow-up questions.",
                },
                {
                    "role": "user",
                    "content": f"Based on this module action: '{user_question}', generate 3 relevant follow-up questions. Return ONLY the questions, one per line.",
                },
            ],
            max_tokens=200,
            temperature=0.7,
        )
        follow_up_text = follow_up_response.choices[0].message.content.strip()
        follow_up_questions = [
            q.strip() for q in follow_up_text.split("\n") if q.strip()
        ][:3]
    except Exception as e:
        logger.warning(f"Follow-up generation failed: {e}")

    return jsonify({
        "answer": answer,
        "sources": [],
        "follow_up_questions": follow_up_questions,
        "action_result": last_function_result,
        "total_documents_searched": collection_count,
    })
