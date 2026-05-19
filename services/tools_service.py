"""
Tools Service — Maps LLM function calls to n8n webhooks.

Provides OpenAI-compatible tool definitions and handles execution
by forwarding calls to n8n webhook endpoints.
"""

import json
import logging
from typing import Any

import aiohttp
from pipecat.frames.frames import FunctionCallResultFrame
from pipecat.services.ai_service import AIService

logger = logging.getLogger(__name__)

# OpenAI function-calling tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "control_smart_home",
            "description": "Control smart home devices (lights, switches, thermostats, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Device name (e.g., 'living room lights')"},
                    "action": {"type": "string", "enum": ["turn_on", "turn_off", "toggle", "set"], "description": "Action to perform"},
                    "location": {"type": "string", "description": "Room or area"},
                    "value": {"type": "string", "description": "Value for 'set' actions (e.g., brightness, temperature)"},
                },
                "required": ["device", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_calendar",
            "description": "Query upcoming calendar events for a date or date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (ISO format or relative like 'today', 'tomorrow')"},
                    "end_date": {"type": "string", "description": "End date (ISO format or relative)"},
                    "query": {"type": "string", "description": "Optional search term to filter events"},
                },
                "required": ["start_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to a contact via Telegram or SMS",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Contact name or identifier"},
                    "message": {"type": "string", "description": "Message content to send"},
                    "platform": {"type": "string", "enum": ["telegram", "sms"], "default": "telegram"},
                },
                "required": ["recipient", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_list",
            "description": "Add an item to a shopping list or todo list",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "Item to add"},
                    "category": {"type": "string", "description": "Category (e.g., groceries, hardware)"},
                    "quantity": {"type": "integer", "description": "Quantity", "default": 1},
                    "list_name": {"type": "string", "description": "Which list to add to", "default": "shopping"},
                },
                "required": ["item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder for a specific time",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder": {"type": "string", "description": "What to be reminded about"},
                    "time": {"type": "string", "description": "When to trigger (ISO datetime or relative like 'in 30 minutes', 'at 3pm')"},
                },
                "required": ["reminder", "time"],
            },
        },
    },
]


class N8nToolsService:
    """Handles function call execution by forwarding to n8n webhooks."""

    def __init__(self, config: dict):
        """
        Args:
            config: The n8n section from config.yaml containing base_url, webhooks, timeout.
        """
        self.base_url = config.get("base_url", "http://localhost:5678")
        self.webhooks = config.get("webhooks", {})
        self.timeout = config.get("timeout", 10)

    def get_tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible tool definitions for the LLM."""
        return TOOL_DEFINITIONS

    async def execute_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        """
        Execute a tool call by POSTing to the corresponding n8n webhook.

        Args:
            function_name: Name of the function to call.
            arguments: Parsed arguments dict from the LLM.

        Returns:
            Result string to feed back into the conversation.
        """
        webhook_path = self.webhooks.get(function_name)
        if not webhook_path:
            return f"Error: No webhook configured for tool '{function_name}'"

        url = f"{self.base_url}{webhook_path}"
        logger.info(f"Calling n8n webhook: {function_name} → {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=arguments,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result", json.dumps(data))
                    else:
                        text = await response.text()
                        logger.error(f"n8n webhook error {response.status}: {text}")
                        return f"Error: webhook returned status {response.status}"
        except aiohttp.ClientError as e:
            logger.error(f"n8n connection error: {e}")
            return f"Error: could not reach n8n webhook ({e})"
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing {function_name}: {e}"


async def handle_function_call(tools_service: N8nToolsService, function_name: str, arguments_json: str) -> str:
    """
    Parse arguments and execute via tools service.

    Args:
        tools_service: The N8nToolsService instance.
        function_name: Function name from LLM.
        arguments_json: JSON string of arguments.

    Returns:
        Result string.
    """
    try:
        arguments = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
    except json.JSONDecodeError:
        return f"Error: could not parse arguments for {function_name}"

    return await tools_service.execute_tool(function_name, arguments)
