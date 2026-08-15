# relation_extractor.py - Extracts relationships between entities.
"""
relation_extractor.py
Extracts typed, directional relationships between entities from research content.

Relationship types: partners_with, uses, supports, founded_by, acquired_by,
                    competes_with, invested_in, works_for, developed_by,
                    part_of, related_to
Returns relationship confidence scores and directional metadata.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SUPPORTED_RELATION_TYPES = [
    "partners_with",
    "uses",
    "supports",
    "founded_by",
    "acquired_by",
    "competes_with",
    "invested_in",
    "works_for",
    "developed_by",
    "part_of",
    "related_to",
]

RELATION_EXTRACTION_PROMPT = """You are an expert knowledge graph relationship extractor for research intelligence.

Given the entities list and the source text, extract all EXPLICIT directional relationships between those entities.
Return a JSON array with objects having these fields:
- "source": the canonical name of the source entity (must be in the entities list)
- "target": the canonical name of the target entity (must be in the entities list)
- "relation": one of [{relation_types}]
- "description": a 1-sentence description of the relationship from the text
- "confidence": a float from 0.0 to 1.0 indicating extraction confidence

Rules:
- Only extract relationships EXPLICITLY stated or strongly implied in the text
- Both source and target MUST be from the provided entities list
- Prefer directional specificity (e.g. "founded_by" not "related_to")
- No self-referential relationships (source != target)
- Return ONLY a valid JSON array, no markdown, no explanation

ENTITIES:
{entities}

TEXT:
{text}

JSON RELATIONSHIPS:"""


@dataclass
class ExtractedRelation:
    """A structured directional relationship between two entities."""
    source: str
    target: str
    relation_type: str
    description: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "description": self.description,
            "confidence": self.confidence,
        }

    def edge_key(self) -> str:
        """Generate a unique key for this directional edge."""
        return f"{self.source}|{self.relation_type}|{self.target}"


class RelationExtractor:
    """
    LLM-powered relationship extractor for knowledge graph construction.
    Takes pre-extracted entities and finds directional relationships between them.
    """

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            try:
                from app.llm.router import get_llm_router
                self._llm = get_llm_router()
            except Exception as e:
                logger.warning(f"LLM router unavailable for relation extraction: {e}")
        return self._llm

    def extract_relations(
        self,
        text: str,
        entity_names: List[str],
        max_length: int = 3000,
        min_entities: int = 2,
    ) -> List[ExtractedRelation]:
        """
        Extract directional relationships between entities from research text.

        Args:
            text: Raw research content
            entity_names: List of entity canonical names to find relations between
            max_length: Maximum text length to send to LLM
            min_entities: Minimum entity count required to attempt extraction

        Returns:
            List of ExtractedRelation objects sorted by confidence descending
        """
        if not text or not text.strip():
            return []
        if len(entity_names) < min_entities:
            logger.debug(f"Insufficient entities ({len(entity_names)}) for relation extraction.")
            return []

        truncated_text = text[:max_length].strip()
        llm = self._get_llm()
        if llm is None:
            logger.warning("No LLM available, skipping relation extraction.")
            return []

        entities_str = "\n".join(f"- {name}" for name in entity_names[:30])
        prompt = RELATION_EXTRACTION_PROMPT.format(
            relation_types=", ".join(SUPPORTED_RELATION_TYPES),
            entities=entities_str,
            text=truncated_text,
        )

        try:
            raw = llm.generate_response(prompt, task_type="relation_extraction")
            relations = self._parse_relations(raw, valid_entities=set(entity_names))
            logger.info(f"Extracted {len(relations)} relationships from text chunk.")
            return sorted(relations, key=lambda r: r.confidence, reverse=True)
        except Exception as e:
            logger.error(f"Relation extraction LLM call failed: {e}")
            return []

    def _parse_relations(
        self, raw_response: str, valid_entities: Optional[set] = None
    ) -> List[ExtractedRelation]:
        """Parse and validate the LLM JSON response into ExtractedRelation objects."""
        relations: List[ExtractedRelation] = []

        # Strip markdown fences
        cleaned = re.sub(r"```(?:json)?", "", raw_response).strip()
        match = re.search(r"\[.*?\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("No JSON array found in relation extraction response.")
            return []

        try:
            raw_list = json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse relation JSON: {e}")
            return []

        seen_edges: set = set()

        for item in raw_list:
            if not isinstance(item, dict):
                continue

            source = item.get("source", "").strip()
            target = item.get("target", "").strip()
            relation = item.get("relation", "related_to").strip().lower()
            description = item.get("description", "").strip()
            confidence = float(item.get("confidence", 0.5))

            # Validate
            if not source or not target:
                continue
            if source == target:
                continue
            if relation not in SUPPORTED_RELATION_TYPES:
                relation = "related_to"
            confidence = max(0.0, min(1.0, confidence))

            # Optionally restrict to known entities
            if valid_entities:
                # Case-insensitive entity matching
                valid_lower = {e.lower(): e for e in valid_entities}
                source = valid_lower.get(source.lower(), source)
                target = valid_lower.get(target.lower(), target)
                if source.lower() not in valid_lower and target.lower() not in valid_lower:
                    continue

            edge_key = f"{source}|{relation}|{target}"
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            relations.append(
                ExtractedRelation(
                    source=source,
                    target=target,
                    relation_type=relation,
                    description=description,
                    confidence=confidence,
                )
            )

        return relations


# Module-level singleton
_relation_extractor_instance: Optional[RelationExtractor] = None


def get_relation_extractor() -> RelationExtractor:
    global _relation_extractor_instance
    if _relation_extractor_instance is None:
        _relation_extractor_instance = RelationExtractor()
    return _relation_extractor_instance
