"""Agent tool definitions for OpenAI function calling."""

from agent.crud import get_module, list_modules, list_category, add_module, update_module, delete_module

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_module",
            "description": "Look up the alphanumeric code for a specific building module by name. Use when the user asks about a specific module's code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "The name of the module to look up",
                    }
                },
                "required": ["module_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_modules",
            "description": "List all modules currently in the module database with their codes. Use when the user asks to see all modules or browse the module list.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_category",
            "description": "List all classification entries whose code starts with a given prefix. Use when the user wants to see all entries in a BIM code category (e.g., '04 05 13' for all mortar types). Shows existing codes and names to help determine the next available code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_prefix": {
                        "type": "string",
                        "description": "The code prefix to filter by (e.g., '04 05 13')",
                    }
                },
                "required": ["category_prefix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_module",
            "description": "Add a new building module with a name, alphanumeric code, and optional description. Use when the user wants to create or add a new module.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "The name for the new module",
                    },
                    "code": {
                        "type": "string",
                        "description": "The alphanumeric code (e.g., 'BLD-001', 'FND-123')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the module",
                    },
                },
                "required": ["module_name", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_module",
            "description": "Update an existing module's alphanumeric code or description. Use when the user wants to change or modify a module.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "The name of the module to update",
                    },
                    "new_code": {
                        "type": "string",
                        "description": "The new alphanumeric code",
                    },
                    "new_description": {
                        "type": "string",
                        "description": "The new description",
                    },
                },
                "required": ["module_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_module",
            "description": "Delete a module from the database. Use when the user wants to remove a module.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "The name of the module to delete",
                    }
                },
                "required": ["module_name"],
            },
        },
    },
]

AGENT_FUNCTION_MAP = {
    "get_module": get_module,
    "list_modules": list_modules,
    "list_category": list_category,
    "add_module": add_module,
    "update_module": update_module,
    "delete_module": delete_module,
}

DESTRUCTIVE_ACTIONS = {"update_module", "delete_module"}
