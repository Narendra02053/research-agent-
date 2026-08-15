from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Abstract Base Class for all MCP-style tools.
    Provides standard interfaces for metadata and execution.
    """
    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool logic.
        Must be implemented by subclasses.
        """
        pass
