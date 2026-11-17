"""
Unified Tool Registry for InsightIQ Agent.

Registers all specialized agent tools, provides metadata schemas, and enables
centralized dynamic tool dispatching during agent workflow execution.
"""

import logging
from typing import Dict, Any, Optional, List
from backend.app.tools.sql_tool import SQLAnalyticsTool, SQLToolOutput
from backend.app.tools.rag_tool import RAGRetrievalTool, RAGToolOutput
from backend.app.tools.python_tool import PythonAnalyticsTool, PythonToolOutput

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry and executor for InsightIQ agent tools."""

    def __init__(
        self,
        sql_tool: Optional[SQLAnalyticsTool] = None,
        rag_tool: Optional[RAGRetrievalTool] = None,
        python_tool: Optional[PythonAnalyticsTool] = None,
    ):
        self.sql_tool = sql_tool or SQLAnalyticsTool()
        self.rag_tool = rag_tool or RAGRetrievalTool()
        self.python_tool = python_tool or PythonAnalyticsTool()

        self._tools = {
            self.sql_tool.name: self.sql_tool,
            self.rag_tool.name: self.rag_tool,
            self.python_tool.name: self.python_tool,
        }

    def list_tools(self) -> List[Dict[str, str]]:
        """Returns metadata for all available registered tools."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Retrieves a tool instance by name."""
        return self._tools.get(tool_name)

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a registered tool by name with provided arguments and returns a dictionary payload.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in ToolRegistry. Available: {list(self._tools.keys())}")

        logger.info(f"Dispatching tool '{tool_name}' with args: {kwargs}")
        result = tool.run(**kwargs)
        if hasattr(result, "to_dict"):
            return result.to_dict()
        return result


# Global singleton registry
tool_registry = ToolRegistry()
