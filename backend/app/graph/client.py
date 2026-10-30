"""Neo4j asynchronous client with connection pooling, health checks, and lifecycle management."""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Manages the Neo4j AsyncDriver connection pool and parameterized Cypher execution."""

    def __init__(self) -> None:
        self._driver = None
        self._database = settings.NEO4J_DATABASE or "neo4j"
        self._uri = settings.NEO4J_URI
        self._user = settings.neo4j_effective_user
        self._password = settings.NEO4J_PASSWORD
        self._max_pool_size = settings.NEO4J_MAX_CONNECTION_POOL_SIZE
        self._conn_timeout = settings.NEO4J_CONNECTION_TIMEOUT
        self._max_lifetime = settings.NEO4J_MAX_CONNECTION_LIFETIME

    async def connect(self) -> bool:
        """Initialize the Neo4j AsyncDriver if not already connected."""
        if self._driver is not None:
            return True

        try:
            from neo4j import AsyncGraphDatabase

            # Secure connection without exposing password in logs
            logger.info("Connecting to Neo4j at %s (user: %s, database: %s)", self._uri, self._user, self._database)
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
                max_connection_pool_size=self._max_pool_size,
                connection_timeout=self._conn_timeout,
                max_connection_lifetime=self._max_lifetime,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
            return True
        except Exception as exc:
            logger.warning("Failed to establish Neo4j connection: %s", exc)
            self._driver = None
            return False

    async def close(self) -> None:
        """Close the Neo4j driver and release all connection pool sockets."""
        if self._driver is not None:
            try:
                await self._driver.close()
                logger.info("Neo4j driver connection pool closed.")
            except Exception as exc:
                logger.warning("Error while closing Neo4j driver: %s", exc)
            finally:
                self._driver = None

    @property
    def is_connected(self) -> bool:
        """Check if driver instance is currently created."""
        return self._driver is not None

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a read/write parameterized Cypher query and return records as dicts."""
        if not self.is_connected:
            connected = await self.connect()
            if not connected or self._driver is None:
                raise ConnectionError("Neo4j database is not reachable")

        target_db = database or self._database
        records_out: List[Dict[str, Any]] = []

        try:
            async with self._driver.session(database=target_db) as session:
                result = await session.run(query, parameters or {})
                async for record in result:
                    records_out.append(record.data())
        except Exception as exc:
            logger.error("Neo4j query execution error: %s", exc, exc_info=True)
            raise

        return records_out

    async def execute_write_transaction(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Any:
        """Execute a parameterized Cypher write transaction."""
        if not self.is_connected:
            connected = await self.connect()
            if not connected or self._driver is None:
                raise ConnectionError("Neo4j database is not reachable")

        target_db = database or self._database

        async with self._driver.session(database=target_db) as session:
            async def tx_work(tx):
                res = await tx.run(query, parameters or {})
                return [r.data() async for r in res]

            return await session.execute_write(tx_work)

    async def check_health(self) -> Dict[str, Any]:
        """Verify Neo4j connectivity and return basic graph topology statistics."""
        try:
            if not self.is_connected:
                connected = await self.connect()
                if not connected:
                    return {
                        "status": "unhealthy",
                        "database": self._database,
                        "connected": False,
                        "error": "Cannot connect to Neo4j instance",
                    }

            # Run light query for connectivity and counts
            counts = await self.execute_query(
                "MATCH (n) RETURN count(n) AS node_count"
            )
            node_count = counts[0]["node_count"] if counts else 0

            rel_counts = await self.execute_query(
                "MATCH ()-[r]->() RETURN count(r) AS rel_count"
            )
            rel_count = rel_counts[0]["rel_count"] if rel_counts else 0

            return {
                "status": "healthy",
                "database": self._database,
                "connected": True,
                "node_count": node_count,
                "relationship_count": rel_count,
            }
        except Exception as exc:
            logger.warning("Neo4j health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "database": self._database,
                "connected": False,
                "error": str(exc),
            }


# Global singleton instance
neo4j_client = Neo4jClient()


def get_neo4j_client() -> Neo4jClient:
    """Return the global Neo4jClient singleton."""
    return neo4j_client


def set_neo4j_client(client: Optional[Neo4jClient]) -> None:
    """Override singleton client for test suites."""
    global neo4j_client
    neo4j_client = client or Neo4jClient()
