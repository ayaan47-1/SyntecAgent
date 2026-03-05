"""
Tests for handle_tool_call() and handle_confirmation() in agent/chat_handlers.py.

Covers:
- No-op when no tool call present
- Single tool execution (non-destructive)
- Message list mutation
- Follow-up LLM receives AGENT_TOOLS
- Multi-step chaining (list_category → add_module)
- Safety cap at 10 iterations
- Destructive action returns pending_action without executing
- handle_confirmation: executes update, rejects invalid type, fallback LLM
"""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, patch as _patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app2 import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_ctx():
    """Push a Flask application context so jsonify() works."""
    with app.app_context():
        yield


@pytest.fixture
def temp_modules_db(tmp_path):
    """Isolated SQLite DB per test."""
    import agent.db as agent_db

    db_path = str(tmp_path / "test.db")
    with patch("agent.db._DB_PATH", db_path):
        if hasattr(agent_db._local, "conn") and agent_db._local.conn is not None:
            try:
                agent_db._local.conn.close()
            except Exception:
                pass
        agent_db._local.__dict__.clear()
        from agent.db import init_db
        init_db()
        yield db_path
        if hasattr(agent_db._local, "conn") and agent_db._local.conn is not None:
            try:
                agent_db._local.conn.close()
            except Exception:
                pass
        agent_db._local.__dict__.clear()


# ---------------------------------------------------------------------------
# Test-object helpers
# ---------------------------------------------------------------------------

def make_tool_call(name, args_dict, call_id="call_1"):
    """Build a MagicMock that looks like an OpenAI tool-call object."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args_dict)
    return tc


def make_response_message(tool_call=None, content=""):
    """Build a MagicMock message with optional tool_call and text content."""
    msg = MagicMock()
    msg.tool_calls = [tool_call] if tool_call else []
    msg.content = content
    msg.model_dump.return_value = {"role": "assistant", "content": content}
    return msg


def make_llm_response(message):
    """Wrap a message mock in a completion-response mock."""
    resp = MagicMock()
    resp.choices[0].message = message
    return resp


# ---------------------------------------------------------------------------
# Basic tool-call handling
# ---------------------------------------------------------------------------

class TestHandleToolCallBasic:

    def test_no_tool_call_returns_none(self):
        """tool_calls=[] → caller receives None and continues its own flow."""
        from agent.chat_handlers import handle_tool_call

        msg = make_response_message(tool_call=None)
        result = handle_tool_call(
            msg, [], "q", str,
            MagicMock(), "model", MagicMock(), "openai-model", None, 0,
        )
        assert result is None

    def test_single_tool_executes_immediately(self, app_ctx, temp_modules_db):
        """Non-destructive tool (get_module) executes and returns a response."""
        from agent.chat_handlers import handle_tool_call

        tc = make_tool_call("get_module", {"module_name": "NoSuchModule"})
        first_msg = make_response_message(tool_call=tc)

        follow_up_msg = make_response_message(content="Module not found.")
        fq_msg = make_response_message(content="Q1\nQ2\nQ3")

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = [
            make_llm_response(follow_up_msg),
            make_llm_response(fq_msg),
        ]

        result = handle_tool_call(
            first_msg, [], "question", str,
            chat_client, "model", MagicMock(), "openai-model", chat_client, 5,
        )

        assert result is not None
        data = result.get_json()
        assert "answer" in data

    def test_tool_result_appended_to_messages(self, app_ctx, temp_modules_db):
        """After tool execution messages grows by 2: assistant role + tool role."""
        from agent.chat_handlers import handle_tool_call

        tc = make_tool_call("get_module", {"module_name": "Nobody"})
        first_msg = make_response_message(tool_call=tc)

        follow_up_msg = make_response_message(content="Done")
        fq_msg = make_response_message(content="")

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = [
            make_llm_response(follow_up_msg),
            make_llm_response(fq_msg),
        ]

        messages = []
        handle_tool_call(
            first_msg, messages, "q", str,
            chat_client, "model", MagicMock(), "m2", chat_client, 0,
        )

        assert len(messages) == 2
        assert messages[1]["role"] == "tool"

    def test_follow_up_llm_receives_tools(self, app_ctx, temp_modules_db):
        """The follow-up LLM call inside the loop is passed tools=AGENT_TOOLS."""
        from agent.chat_handlers import handle_tool_call
        from agent.tools import AGENT_TOOLS

        tc = make_tool_call("get_module", {"module_name": "X"})
        first_msg = make_response_message(tool_call=tc)

        follow_up_msg = make_response_message(content="Done")
        fq_msg = make_response_message(content="")

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = [
            make_llm_response(follow_up_msg),
            make_llm_response(fq_msg),
        ]

        handle_tool_call(
            first_msg, [], "q", str,
            chat_client, "model", MagicMock(), "m2", chat_client, 0,
        )

        # First .create() call is the follow-up loop LLM (not follow-up questions)
        first_kwargs = chat_client.chat.completions.create.call_args_list[0].kwargs
        assert "tools" in first_kwargs
        assert first_kwargs["tools"] == AGENT_TOOLS

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_two_tool_calls_chain(self, mock_emb, mock_coll, app_ctx, temp_modules_db):
        """list_category → add_module chain: both tools execute, final answer returned."""
        from agent.chat_handlers import handle_tool_call

        # Initial: list_category
        lc_tc = make_tool_call(
            "list_category", {"category_prefix": "04 05 13"}, call_id="call_lc"
        )
        initial_msg = make_response_message(tool_call=lc_tc)

        # After list_category: add_module
        am_tc = make_tool_call(
            "add_module",
            {"module_name": "New Mortar", "code": "04 05 13.A9", "description": "New"},
            call_id="call_am",
        )
        after_lc_msg = make_response_message(tool_call=am_tc)

        # After add_module: plain text
        final_msg = make_response_message(content="Both tools ran.")
        fq_msg = make_response_message(content="")

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = [
            make_llm_response(after_lc_msg),   # loop iter 1 follow-up
            make_llm_response(final_msg),       # loop iter 2 follow-up
            make_llm_response(fq_msg),          # follow-up questions
        ]

        result = handle_tool_call(
            initial_msg, [], "add mortar", str,
            chat_client, "model", MagicMock(), "m2", chat_client, 0,
        )

        assert result is not None
        data = result.get_json()
        assert data["answer"] == "Both tools ran."
        # 2 tool-loop calls + 1 follow-up questions call
        assert chat_client.chat.completions.create.call_count == 3

    def test_safety_cap_at_10(self, app_ctx, temp_modules_db):
        """LLM always returns a tool call → loop exits after 10 iterations."""
        from agent.chat_handlers import handle_tool_call

        def always_tool_response(*args, **kwargs):
            tc = make_tool_call("list_modules", {})
            msg = make_response_message(tool_call=tc, content="")
            return make_llm_response(msg)

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = always_tool_response

        initial_tc = make_tool_call("list_modules", {})
        initial_msg = make_response_message(tool_call=initial_tc)

        result = handle_tool_call(
            initial_msg, [], "q", str,
            chat_client, "model", MagicMock(), "m2", chat_client, 0,
        )

        assert result is not None
        # 10 loop iterations + 1 follow-up questions = 11 total .create() calls
        assert chat_client.chat.completions.create.call_count == 11


# ---------------------------------------------------------------------------
# Destructive actions
# ---------------------------------------------------------------------------

class TestHandleToolCallDestructive:

    def test_destructive_returns_pending_action(self, app_ctx, temp_modules_db):
        """update_module → returns pending_action dict without executing."""
        from agent.chat_handlers import handle_tool_call

        tc = make_tool_call(
            "update_module", {"module_name": "TestMod", "new_code": "NEW-001"}
        )
        msg = make_response_message(tool_call=tc)

        result = handle_tool_call(
            msg, [], "update module", str,
            MagicMock(), "model", MagicMock(), "m2", None, 0,
        )

        assert result is not None
        data = result.get_json()
        assert "pending_action" in data
        assert data["pending_action"]["type"] == "update_module"

    def test_destructive_delete_returns_pending_action(self, app_ctx, temp_modules_db):
        """delete_module → returns pending_action dict without executing."""
        from agent.chat_handlers import handle_tool_call

        tc = make_tool_call("delete_module", {"module_name": "TestMod"})
        msg = make_response_message(tool_call=tc)

        result = handle_tool_call(
            msg, [], "delete module", str,
            MagicMock(), "model", MagicMock(), "m2", None, 0,
        )

        assert result is not None
        data = result.get_json()
        assert "pending_action" in data
        assert data["pending_action"]["type"] == "delete_module"

    def test_destructive_does_not_execute(self, app_ctx, temp_modules_db):
        """The CRUD function for a destructive action is NEVER called."""
        from agent.chat_handlers import handle_tool_call
        from agent.tools import AGENT_FUNCTION_MAP

        mock_update = MagicMock()
        with patch.dict(AGENT_FUNCTION_MAP, {"update_module": mock_update}):
            tc = make_tool_call(
                "update_module", {"module_name": "TestMod", "new_code": "X"}
            )
            msg = make_response_message(tool_call=tc)

            handle_tool_call(
                msg, [], "update module", str,
                MagicMock(), "model", MagicMock(), "m2", None, 0,
            )

        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# handle_confirmation
# ---------------------------------------------------------------------------

class TestHandleConfirmation:

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_confirmation_executes_update(
        self, mock_emb, mock_coll, app_ctx, temp_modules_db
    ):
        """Confirmed update_module runs CRUD and returns the action result."""
        from agent.chat_handlers import handle_confirmation
        from agent.crud import add_module

        add_module("Update Me", "UM-001")

        summary_msg = MagicMock()
        summary_msg.content = "Updated!"
        summary_response = MagicMock()
        summary_response.choices[0].message = summary_msg

        chat_client = MagicMock()
        chat_client.chat.completions.create.return_value = summary_response

        result = handle_confirmation(
            {"type": "update_module", "params": {
                "module_name": "Update Me", "new_code": "UM-002"
            }},
            str,
            chat_client, "model",
            MagicMock(), "openai-model",
        )

        data = result.get_json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["new_code"] == "UM-002"
        assert data["answer"] == "Updated!"

    def test_confirmation_invalid_type_returns_400(self, app_ctx, temp_modules_db):
        """Action type not in DESTRUCTIVE_ACTIONS → 400 JSON error response."""
        from agent.chat_handlers import handle_confirmation

        result = handle_confirmation(
            {"type": "get_module", "params": {}},  # not a destructive action
            str,
            MagicMock(), "model",
            MagicMock(), "openai-model",
        )

        assert isinstance(result, tuple)
        response, status_code = result
        assert status_code == 400
        data = response.get_json()
        assert "error" in data

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_confirmation_llm_fallback(

        self, mock_emb, mock_coll, app_ctx, temp_modules_db
    ):
        """Primary LLM raises → falls back to openai_client for summary."""
        from agent.chat_handlers import handle_confirmation
        from agent.crud import add_module

        add_module("Fallback Mod", "FM-001")

        chat_client = MagicMock()
        chat_client.chat.completions.create.side_effect = Exception("DeepSeek down")

        fallback_msg = MagicMock()
        fallback_msg.content = "Fallback answer"
        fallback_response = MagicMock()
        fallback_response.choices[0].message = fallback_msg

        openai_client = MagicMock()
        openai_client.chat.completions.create.return_value = fallback_response

        result = handle_confirmation(
            {"type": "update_module", "params": {
                "module_name": "Fallback Mod", "new_code": "FM-002"
            }},
            str,
            chat_client, "deepseek-model",
            openai_client, "gpt-4o",
        )

        data = result.get_json()
        assert data["answer"] == "Fallback answer"
        openai_client.chat.completions.create.assert_called_once()


# ---------------------------------------------------------------------------
# P0-4: Malformed tool-call JSON
# ---------------------------------------------------------------------------

class TestHandleToolCallEdgeCases:

    def test_malformed_tool_call_json_returns_400(self, app_ctx, temp_modules_db):
        """If LLM returns malformed JSON arguments, handle_tool_call returns 400."""
        from agent.chat_handlers import handle_tool_call

        tc = MagicMock()
        tc.id = "call_bad"
        tc.function.name = "get_module"
        tc.function.arguments = "{not valid json}"

        msg = MagicMock()
        msg.tool_calls = [tc]
        msg.content = ""
        msg.model_dump.return_value = {"role": "assistant", "content": ""}

        result = handle_tool_call(
            msg, [], "question", str,
            MagicMock(), "model", MagicMock(), "openai-model", None, 0,
        )

        assert result is not None
        response, status_code = result
        assert status_code == 400
        data = response.get_json()
        assert "error" in data
