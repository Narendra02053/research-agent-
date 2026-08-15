import json
import re
import logging
from pydantic import BaseModel
from typing import Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

def parse_and_validate_json(text: str, model_class: Type[T]) -> T:
    """
    Extracts JSON from text, parses it, and validates it against a Pydantic model.
    Handles markdown code blocks and random conversational text before/after the JSON.
    """
    cleaned = text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end+1]
        
    try:
        data = json.loads(cleaned)
        return model_class.model_validate(data)
    except Exception as e:
        logger.error(f"JSON parsing/validation failed: {e}. Raw input:\n{text}")
        raise ValueError(f"Failed to parse or validate JSON for {model_class.__name__}: {str(e)}") from e
