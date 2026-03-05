"""Agent package — module management system extracted from app2.py."""

from agent.crud import get_module, list_modules, list_category, add_module, update_module, delete_module
from agent.tools import AGENT_TOOLS, AGENT_FUNCTION_MAP, DESTRUCTIVE_ACTIONS
from agent.routes import create_modules_blueprint
from agent.chat_handlers import handle_confirmation, handle_tool_call
