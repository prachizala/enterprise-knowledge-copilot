"""Entity linking: grounds query mentions to canonical database entities."""

import logging
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.retrieval.schemas import LinkedEntity

logger = logging.getLogger(__name__)


class EntityLinker:
    """Links free-text entity mentions in user queries to structured Entity records."""

    @staticmethod
    async def link_mentions(
        db: AsyncSession,
        mentions: List[str],
        min_confidence: float = 0.60,
    ) -> List[LinkedEntity]:
        """Ground a list of string mentions extracted from the query to canonical Entities."""
        if not mentions:
            return []

        linked_results: List[LinkedEntity] = []
        seen_entity_ids = set()

        for mention in mentions:
            clean_mention = mention.strip()
            if not clean_mention or len(clean_mention) < 2:
                continue

            # 1. Exact match (case-insensitive)
            exact_stmt = select(Entity).where(
                or_(
                    Entity.canonical_name.ilike(clean_mention),
                    Entity.display_name.ilike(clean_mention),
                )
            )
            exact_matches = (await db.execute(exact_stmt)).scalars().all()

            if exact_matches:
                primary = exact_matches[0]
                is_ambiguous = len(exact_matches) > 1
                alternatives = [
                    {
                        "entity_id": m.id,
                        "canonical_name": m.canonical_name,
                        "entity_type": m.entity_type,
                    }
                    for m in exact_matches[1:]
                ]

                if primary.id not in seen_entity_ids:
                    seen_entity_ids.add(primary.id)
                    linked_results.append(
                        LinkedEntity(
                            entity_id=primary.id,
                            canonical_name=primary.canonical_name,
                            display_name=primary.display_name,
                            entity_type=primary.entity_type,
                            mention_text=clean_mention,
                            confidence=0.98 if not is_ambiguous else 0.85,
                            match_type="exact",
                            is_ambiguous=is_ambiguous,
                            candidate_alternatives=alternatives,
                        )
                    )
                continue

            # 2. Substring / normalized match
            sub_stmt = (
                select(Entity)
                .where(
                    or_(
                        Entity.canonical_name.ilike(f"%{clean_mention}%"),
                        Entity.display_name.ilike(f"%{clean_mention}%"),
                    )
                )
                .limit(5)
            )
            sub_matches = (await db.execute(sub_stmt)).scalars().all()

            if sub_matches:
                primary = sub_matches[0]
                is_ambiguous = len(sub_matches) > 1
                alternatives = [
                    {
                        "entity_id": m.id,
                        "canonical_name": m.canonical_name,
                        "entity_type": m.entity_type,
                    }
                    for m in sub_matches[1:]
                ]

                if primary.id not in seen_entity_ids:
                    seen_entity_ids.add(primary.id)
                    linked_results.append(
                        LinkedEntity(
                            entity_id=primary.id,
                            canonical_name=primary.canonical_name,
                            display_name=primary.display_name,
                            entity_type=primary.entity_type,
                            mention_text=clean_mention,
                            confidence=0.78,
                            match_type="normalized",
                            is_ambiguous=is_ambiguous,
                            candidate_alternatives=alternatives,
                        )
                    )

        return linked_results
