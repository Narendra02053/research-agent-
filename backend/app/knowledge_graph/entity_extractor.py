"""
entity_extractor.py
Extracts named entities from research content using LLM-based structured extraction.

Entity types: company, person, technology, product, framework, financial_entity, organization
Returns normalized entity names, types, descriptions, and confidence scores.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SUPPORTED_ENTITY_TYPES = [
    "company",
    "person",
    "technology",
    "product",
    "framework",
    "financial_entity",
    "organization",
]

ENTITY_EXTRACTION_PROMPT = """You are an expert Named Entity Recognition (NER) system specialized in research and business intelligence.

Extract ALL significant named entities from the text below. For each entity, return a JSON array with objects having these fields:
- "name": the canonical, normalized entity name (string)
- "type": one of [{entity_types}]
- "description": a 1-sentence description based on the text (string)
- "confidence": a float from 0.0 to 1.0 indicating extraction confidence
- "aliases": a list of alternative names or abbreviations found in the text (list of strings)

Rules:
- Normalize entity names to their canonical form (e.g. "NVIDIA Corporation" not "nvidia")
- Only include entities explicitly mentioned or clearly implied in the text
- Do NOT include generic terms, pronouns, or vague references
- Confidence > 0.7 = highly confident, 0.4-0.7 = moderate, < 0.4 = low confidence
- Return ONLY a valid JSON array, no markdown, no explanation

TEXT:
{text}

JSON ENTITIES:"""


@dataclass
class ExtractedEntity:
    """A structured entity extracted from research content."""
    name: str
    entity_type: str
    description: str
    confidence: float
    aliases: List[str] = field(default_factory=list)
    source_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "confidence": self.confidence,
            "aliases": self.aliases,
            "source_text": self.source_text[:200] if self.source_text else "",
        }

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize an entity name for deduplication."""
        return re.sub(r"\s+", " ", name.strip().lower())


class EntityExtractor:
    """
    LLM-powered Named Entity Recognition for research content.
    Uses the LLMRouter gateway for extraction and falls back gracefully.
    """

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """Lazy-load the LLM router to avoid circular imports."""
        if self._llm is None:
            try:
                from app.llm.router import get_llm_router
                self._llm = get_llm_router()
            except Exception as e:
                logger.warning(f"LLM router unavailable for entity extraction: {e}")
        return self._llm

    def extract_entities(
        self, text: str, max_length: int = 3000
    ) -> List[ExtractedEntity]:
        """
        Extract named entities from research text using LLM.

        Args:
            text: Raw research content to extract entities from
            max_length: Maximum character length to send to LLM

        Returns:
            List of ExtractedEntity objects sorted by confidence descending
        """
        if not text or not text.strip():
            return []

        # Truncate to avoid token overflow
        truncated_text = text[:max_length].strip()

        llm = self._get_llm()
        if llm is None:
            logger.warning("No LLM available, skipping entity extraction.")
            return []

        prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types=", ".join(SUPPORTED_ENTITY_TYPES),
            text=truncated_text,
        )

        try:
            raw = llm.generate_response(prompt, task_type="entity_extraction")
            entities = self._parse_entities(raw, source_text=truncated_text)
            logger.info(f"Extracted {len(entities)} entities from text chunk.")
            return sorted(entities, key=lambda e: e.confidence, reverse=True)
        except Exception as e:
            logger.error(f"Entity extraction LLM call failed: {e}")
            return []

    def _parse_entities(
        self, raw_response: str, source_text: str = ""
    ) -> List[ExtractedEntity]:
        """Parse and validate the LLM JSON response into ExtractedEntity objects."""
        entities: List[ExtractedEntity] = []

        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw_response).strip()
        # Extract the first JSON array found
        match = re.search(r"\[.*?\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("No JSON array found in entity extraction response.")
            return []

        try:
            raw_list = json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse entity JSON: {e}")
            return []

        for item in raw_list:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "").strip()
            entity_type = item.get("type", "").strip().lower()
            description = item.get("description", "").strip()
            confidence = float(item.get("confidence", 0.5))
            aliases = item.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []

            # Validate
            if not name:
                continue
            if entity_type not in SUPPORTED_ENTITY_TYPES:
                entity_type = "organization"  # default fallback
            confidence = max(0.0, min(1.0, confidence))

            entities.append(
                ExtractedEntity(
                    name=name,
                    entity_type=entity_type,
                    description=description,
                    confidence=confidence,
                    aliases=aliases,
                    source_text=source_text[:200],
                )
            )

        return entities


# Module-level singleton
_entity_extractor_instance: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    global _entity_extractor_instance
    if _entity_extractor_instance is None:
        _entity_extractor_instance = EntityExtractor()
    return _entity_extractor_instance
