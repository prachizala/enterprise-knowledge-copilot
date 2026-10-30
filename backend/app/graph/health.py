"""Neo4j graph database health checks."""

import logging
from typing import Any, Dict

from app.graph.client import get_neo4j_client

logger = logging.getLogger(__name__)


async def check_neo4j_health() -> Dict[str, Any]:
    """Verify Neo4j connectivity and return non-sensitive health metadata."""
    client = get_neo4j_client()
    return await client.check_health()
