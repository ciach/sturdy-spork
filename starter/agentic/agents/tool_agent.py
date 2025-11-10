"""
Tool Agent - Executes database operations and actions.
"""

from typing import Dict, Any, List, Callable
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agentic.tools.database_tools import (
    get_user_info,
    get_subscription_status,
    get_reservations,
    cancel_reservation,
    check_account_status,
    request_refund,
    AVAILABLE_TOOLS,
)


class ToolAgent:
    """
    Agent responsible for executing tools and database operations.
    """

    def __init__(self):
        self.tools = AVAILABLE_TOOLS

    def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool

        Returns:
            Tool execution results
        """
        try:
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "available_tools": list(self.tools.keys()),
                }

            tool_function = self.tools[tool_name]
            result = tool_function(**parameters)

            return {
                "success": True,
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
            }

        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid parameters for tool '{tool_name}': {str(e)}",
                "tool_name": tool_name,
                "parameters": parameters,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}",
                "tool_name": tool_name,
                "parameters": parameters,
            }

    def execute_multiple_tools(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tools in sequence.

        Args:
            tool_calls: List of tool calls, each with 'tool_name' and 'parameters'

        Returns:
            List of tool execution results
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            result = self.execute_tool(tool_name, parameters)
            results.append(result)

        return results

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())

    def format_tool_result(self, result: Dict[str, Any]) -> str:
        """
        Format tool result for human-readable output.

        Args:
            result: Tool execution result

        Returns:
            Formatted string
        """
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        tool_result = result.get("result", {})

        if not tool_result.get("success"):
            return f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"

        # Format based on tool type
        tool_name = result.get("tool_name")

        if tool_name == "get_user_info":
            return f"User: {tool_result.get('full_name')} ({tool_result.get('email')})\nStatus: {'Blocked' if tool_result.get('is_blocked') else 'Active'}"

        elif tool_name == "get_subscription_status":
            return f"Subscription: {tool_result.get('tier')} tier\nStatus: {tool_result.get('status')}\nMonthly Quota: {tool_result.get('monthly_quota')} experiences"

        elif tool_name == "get_reservations":
            count = tool_result.get("count", 0)
            if count == 0:
                return "No reservations found"
            reservations = tool_result.get("reservations", [])
            formatted = f"Found {count} reservation(s):\n"
            for res in reservations[:5]:  # Limit to 5
                exp = res.get("experience", {})
                formatted += f"- {exp.get('title', 'Unknown')} ({res.get('status')})\n"
            return formatted

        elif tool_name == "cancel_reservation":
            return tool_result.get("message", "Reservation cancelled successfully")

        elif tool_name == "check_account_status":
            status = tool_result.get("status", "unknown")
            return f"Account Status: {status}"

        elif tool_name == "request_refund":
            return tool_result.get("message", "Refund request submitted")

        else:
            return str(tool_result)
