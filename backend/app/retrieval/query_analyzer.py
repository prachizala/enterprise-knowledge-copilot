"""Deterministic query analysis and category classification."""

import re
from typing import Any, Dict, List, Tuple
from app.retrieval.schemas import QueryAnalysis

DEPARTMENTS = ["Engineering", "Legal", "Security", "Product", "Operations", "Finance", "HR", "DevOps"]

MULTI_HOP_PATTERNS = [
    r"(?:technolog\w+|tools?)\s+used\s+by\s+projects?\s+(?:managed|led)\s+by",
    r"(?:projects?|systems?)\s+affected\s+by\s+polic\w+",
    r"(?:who|which)\s+.*?\s+(?:uses|depends\s+on)\s+.*?\s+(?:managed|owned)\s+by",
    r"managed\s+by\s+.*?\s+and\s+(?:uses|depends|implements)",
    r"relationship\s+between\s+.*?\s+and\s+.*?\s+through",
]

POLICY_KEYWORDS = {"policy", "compliance", "retention", "standard", "mandate", "regulation", "gdpr", "soc2", "hipaa", "security"}
TECH_KEYWORDS = {"technology", "technologies", "tech", "database", "stack", "framework", "infrastructure", "aws", "cloud", "postgres", "neo4j"}
PROJECT_KEYWORDS = {"project", "initiative", "platform", "system", "engine"}
ORG_KEYWORDS = {"department", "division", "team", "organization", "works for", "reports to"}
COMPARE_KEYWORDS = {"compare", "difference between", "versus", "vs", "differences"}


class QueryAnalyzer:
    """Analyzes and categorizes queries for targeted hybrid GraphRAG retrieval."""

    @staticmethod
    def analyze(query: str) -> QueryAnalysis:
        cleaned = query.strip()
        lower_query = cleaned.lower()

        # 1. Multi-hop detection
        is_multi_hop = False
        for pat in MULTI_HOP_PATTERNS:
            if re.search(pat, lower_query):
                is_multi_hop = True
                break

        # Count entity-like hops or connectives
        if (" which " in lower_query or " that " in lower_query) and (" managed by " in lower_query or " uses " in lower_query or " owns " in lower_query):
            is_multi_hop = True

        # 2. Comparison detection
        requires_comparison = any(k in lower_query for k in COMPARE_KEYWORDS)

        # 3. Category classification
        tokens = set(re.findall(r"\b\w+\b", lower_query))

        if is_multi_hop:
            category = "multi_hop_query"
        elif requires_comparison:
            category = "comparison_query"
        elif tokens & POLICY_KEYWORDS:
            category = "policy_lookup"
        elif tokens & TECH_KEYWORDS:
            category = "technology_lookup"
        elif tokens & PROJECT_KEYWORDS:
            category = "project_lookup"
        elif tokens & ORG_KEYWORDS:
            category = "organizational_query"
        elif any(phrase in lower_query for phrase in ["who manages", "who owns", "who authored", "relationship between", "connected to"]):
            category = "relationship_query"
        elif any(phrase in lower_query for phrase in ["who is", "what is", "tell me about"]):
            category = "entity_lookup"
        elif "document" in lower_query or "file" in lower_query:
            category = "document_lookup"
        else:
            category = "factual_lookup"

        # 4. Extract Entity Mentions (Named entities, Capitalized sequences, Quoted strings)
        detected_entities: List[str] = []

        # Quoted strings
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", cleaned)
        for q in quoted:
            if len(q.strip()) > 1:
                detected_entities.append(q.strip())

        # Capitalized multi-word sequences (e.g., "Alice Smith", "Project Alpha", "Security Policy 2026")
        capitalized_matches = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)+\b", cleaned)
        for cap in capitalized_matches:
            # Filter out sentence beginnings if trivial
            if cap not in detected_entities:
                detected_entities.append(cap)

        # Capitalized single tokens (excluding common question words)
        skip_words = {"What", "Who", "Where", "When", "Why", "How", "Which", "Is", "Are", "Can", "Could", "The", "In", "On", "At", "A", "An"}
        single_caps = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", cleaned)
        for cap in single_caps:
            if cap not in skip_words and cap not in detected_entities:
                # Check if it is a known department
                if cap not in DEPARTMENTS and not any(cap in de for de in detected_entities):
                    detected_entities.append(cap)

        # 5. Extract Filters
        extracted_filters: Dict[str, Any] = {}
        for dept in DEPARTMENTS:
            if re.search(rf"\b(?:in|for|from)\s+{dept}\b", cleaned, re.IGNORECASE):
                extracted_filters["department"] = dept
                break

        # Document name filter cue
        doc_match = re.search(r"\b(?:in|from)\s+(?:document\s+)?([A-Za-z0-9_\-\.]+\.(?:pdf|docx|txt|csv))\b", cleaned, re.IGNORECASE)
        if doc_match:
            extracted_filters["document_filename"] = doc_match.group(1)

        return QueryAnalysis(
            raw_query=cleaned,
            normalized_query=lower_query,
            query_category=category,
            detected_entities=detected_entities,
            extracted_filters=extracted_filters,
            is_multi_hop=is_multi_hop,
            requires_comparison=requires_comparison,
        )
