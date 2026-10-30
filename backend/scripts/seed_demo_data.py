"""
Enterprise Knowledge Copilot — Demo Data Seeder Script.

Seeds:
1. Enterprise Administrator & Manager user accounts.
2. 3 Comprehensive Enterprise Documents across IT, HR, and Engineering.
3. Automatically runs the 6-stage Ingestion Pipeline:
   - Text Extraction
   - Structure-Aware Chunking (headings, tables, page bounds)
   - 1536D Vector Embeddings Generation
   - Named Entity Recognition & Normalization
   - Typed Relationship Extraction
   - Neo4j Knowledge Graph Topology Sync (with graceful fallback if Neo4j is offline)
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.user import User, UserRole
from app.models.document import Document
from app.auth.security import hash_password
from app.services.storage_service import storage_service
from app.services.document_service import document_service
from app.ingestion.orchestrator import DocumentIngestionOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo_data")

DEMO_USERS = [
    {
        "email": "admin@enterprise.local",
        "password": "AdminPassword123!",
        "full_name": "Alex Morgan (Enterprise Admin)",
        "role": UserRole.ADMIN,
        "department": "IT Security",
    },
    {
        "email": "manager@enterprise.local",
        "password": "ManagerPassword123!",
        "full_name": "Jordan Vance (Engineering Manager)",
        "role": UserRole.MANAGER,
        "department": "Engineering",
    },
    {
        "email": "employee@enterprise.local",
        "password": "EmployeePassword123!",
        "full_name": "Sam Taylor (Product Specialist)",
        "role": UserRole.EMPLOYEE,
        "department": "Human Resources",
    },
]

DEMO_DOCUMENTS = [
    {
        "filename": "acme_cloud_security_policy_2026.txt",
        "original_filename": "ACME_Cloud_Security_Policy_2026.txt",
        "department": "IT Security",
        "owner": "admin@enterprise.local",
        "description": "Enterprise cloud security architecture, FIDO2 MFA, AES-256 database vault encryption, and ISO 27001 disaster recovery SLAs.",
        "content": """# ACME Corp Cloud Infrastructure & Zero Trust Security Policy 2026

## 1. Authentication & Identity Management
All employees and contractors must authenticate through Okta SSO with mandatory FIDO2 WebAuthn hardware keys.
Password credentials must be at least 16 alphanumeric characters and expire every 90 days.
Zero Trust network access requires all developer workstations to run compliant Crowdstrike endpoint sensors.

## 2. Database Encryption Standards
Enterprise data stores including PostgreSQL and Neo4j must enforce AES-256 encryption at rest.
All network traffic in transit must strictly enforce TLS 1.3 with automated certificate rotation via Let's Encrypt and AWS Certificate Manager.
Database connection strings must be dynamically injected via HashiCorp Vault.

## 3. Disaster Recovery and SLA Requirements
The Recovery Point Objective (RPO) is strictly defined as less than 15 minutes.
The Recovery Time Objective (RTO) is guaranteed to be less than 2 hours for all tier-1 production systems.
Automated database snapshots are replicated across AWS us-east-1 and us-west-2 regions daily.
Compliance audits are performed biannually to maintain ISO 27001 and SOC 2 Type II certifications.
""",
    },
    {
        "filename": "acme_global_remote_work_handbook_2026.txt",
        "original_filename": "ACME_Global_Remote_Work_Handbook_2026.txt",
        "department": "Human Resources",
        "owner": "employee@enterprise.local",
        "description": "Comprehensive remote work policies, home office equipment stipends, core synchronous hours, and annual leave guidelines.",
        "content": """# ACME Corp Global Remote Work Guidelines & Employee Benefits Handbook 2026

## 1. Remote Work Eligibility and Home Office Stipend
All full-time employees are eligible for full-time distributed remote work across approved international jurisdictions.
ACME Corp provides an annual home office and wellness stipend of $1,200 USD per calendar year.
This stipend covers ergonomic desks, 4K monitors, ergonomic seating, high-speed fiber internet, and gym memberships.

## 2. Core Collaboration and Meeting Hours
To ensure seamless asynchronous and synchronous collaboration across global timezones,
all team members are requested to be available during core collaboration hours from 10:00 AM to 3:00 PM Eastern Standard Time (EST).
Slack and Zoom are the official communication platforms for daily engineering and cross-functional syncs.

## 3. Paid Time Off (PTO) and Health Insurance
Full-time employees receive 25 days of annual paid time off (PTO) alongside unlimited personal sick leave.
ACME Corp sponsors 100% of comprehensive health, dental, and vision insurance premiums for employees and eligible dependents.
Parental leave is provided at 16 weeks of 100% paid leave for all new parents following birth or adoption.
""",
    },
    {
        "filename": "project_apollo_architecture_roadmap_2026.txt",
        "original_filename": "Project_Apollo_Architecture_Roadmap_2026.txt",
        "department": "Engineering",
        "owner": "manager@enterprise.local",
        "description": "Technical specifications for Project Apollo, Apache Kafka event streaming, Neo4j GraphRAG, and pgvector cosine indexing.",
        "content": """# Project Apollo Distributed Microservices Roadmap & GraphRAG Architecture Specs

## 1. Executive Summary & Goals
Project Apollo is ACME Corp's next-generation enterprise knowledge retrieval platform.
The system unifies unstructured document stores, structured PostgreSQL databases, and knowledge graphs into an intelligent copilot.
Target latency for conversational token streaming is sub-200ms with strict zero-hallucination grounded truth citations.

## 2. Architecture & Event Streaming
Microservices communicate through high-throughput Apache Kafka event topics with protobuf schemas.
Internal inter-service RPC calls leverage HTTP/2 and gRPC with mutual TLS (mTLS).
The ingestion orchestrator executes asynchronous pipeline stages for extraction, structure-aware chunking, and embedding generation.

## 3. Knowledge Graph & Vector Retrieval Subsystem
The semantic retrieval engine utilizes pgvector with Hierarchical Navigable Small World (HNSW) indexing.
Enterprise entities (projects, organizations, protocols, technologies) are mapped into a Neo4j 5.20 knowledge graph.
Multi-hop Cypher queries expand candidate contexts up to 2 hops, fused with dense vector search via Reciprocal Rank Fusion (RRF).
""",
    },
]


async def seed_users():
    """Seed default RBAC users if not present."""
    async with AsyncSessionLocal() as session:
        for u in DEMO_USERS:
            res = await session.execute(select(User).where(User.email == u["email"]))
            existing = res.scalars().first()
            if existing:
                logger.info(f"User '{u['email']}' already exists; skipping.")
                continue

            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                department=u["department"],
                is_active=True,
            )
            session.add(user)
            await session.commit()
            logger.info(f"Created demo user: {u['email']} [{u['role'].value}]")


async def seed_documents_and_pipeline():
    """Seed documents and run the full 6-stage ingestion pipeline."""
    orchestrator = DocumentIngestionOrchestrator()

    async with AsyncSessionLocal() as session:
        for doc_data in DEMO_DOCUMENTS:
            res = await session.execute(
                select(Document).where(Document.filename == doc_data["filename"])
            )
            existing = res.scalars().first()
            if existing:
                if existing.status == "processed":
                    logger.info(f"Document '{doc_data['filename']}' is already fully processed; skipping.")
                    continue
                else:
                    logger.info(f"Removing partially processed document '{doc_data['filename']}' for fresh reseed...")
                    await session.delete(existing)
                    await session.commit()

            content_bytes = doc_data["content"].encode("utf-8")
            doc_id = str(uuid.uuid4())

            # 1. Save file to storage
            _, rel_path = storage_service.save_file(
                document_id=doc_id,
                original_filename=doc_data["original_filename"],
                content_bytes=content_bytes,
            )

            # 2. Register Document record
            doc = await document_service.create_document_from_upload(
                db=session,
                filename=doc_data["filename"],
                original_filename=doc_data["original_filename"],
                file_type="txt",
                file_size=len(content_bytes),
                department=doc_data["department"],
                owner=doc_data["owner"],
                description=doc_data["description"],
                storage_path=rel_path,
                mime_type="text/plain",
                doc_id=doc_id,
            )
            logger.info(f"Registered document '{doc.filename}' (ID: {doc.id})")

            # 3. Run full 6-stage Ingestion Pipeline
            logger.info(f"Executing Ingestion Pipeline for '{doc.filename}'...")
            try:
                job = await orchestrator.run_pipeline(
                    db=session,
                    document_id=doc.id,
                )
                logger.info(
                    f"Pipeline completed for '{doc.filename}' with status: {job.status} (progress: {job.progress_pct}%)"
                )
            except Exception as e:
                logger.warning(f"Pipeline executed with non-fatal notice for '{doc.filename}': {e}")


async def main():
    logger.info("==================================================================")
    logger.info("Starting Enterprise Knowledge Copilot Demo Data Seeder...")
    logger.info("==================================================================")

    # Ensure tables exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_users()
    await seed_documents_and_pipeline()

    logger.info("==================================================================")
    logger.info("Demo Data Seeding Finished Successfully!")
    logger.info("Default Login Credentials:")
    logger.info("  Admin:    admin@enterprise.local    / AdminPassword123!")
    logger.info("  Manager:  manager@enterprise.local  / ManagerPassword123!")
    logger.info("  Employee: employee@enterprise.local / EmployeePassword123!")
    logger.info("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
