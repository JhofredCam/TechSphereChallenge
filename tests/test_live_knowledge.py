from __future__ import annotations

from app.config import Settings
from app.database import init_database
from app.schemas import DocumentStatus
from app.services.agent import AgentService
from app.services.documents import DocumentService
from app.services.rag import RagService


def test_uploaded_knowledge_is_searchable_and_deleted_knowledge_is_forgotten(tmp_path):
    settings = Settings(data_dir=tmp_path, chunk_size=200, chunk_overlap=20)
    database = init_database(settings)
    documents = DocumentService(database, settings)
    rag = RagService(database)

    uploaded = documents.upload(
        "La señal posoperatoria lunaria exige contactar al equipo clínico.".encode(
            "utf-8"
        ),
        "guía con espacios.txt",
    )

    assert uploaded.status is DocumentStatus.AVAILABLE
    assert uploaded.id == uploaded.sha256
    assert documents.corpus_revision == 1

    found = rag.search("senal lunaria", limit=3)
    assert len(found) == 1
    assert found[0].document_id == uploaded.id
    assert found[0].page_number == 1
    assert found[0].citation == "guía con espacios.txt (p. 1)"
    assert found[0].corpus_revision == 1

    agent = AgentService(rag, api_key="")
    learned = agent.respond("Que indica la señal lunaria?")
    assert learned.grounded is True
    assert found[0].chunk_id in learned.source_ids
    assert "guía con espacios.txt" in learned.text

    duplicate = documents.upload(
        "La señal posoperatoria lunaria exige contactar al equipo clínico.".encode(
            "utf-8"
        ),
        "renamed.txt",
    )
    assert duplicate.id == uploaded.id
    assert documents.corpus_revision == 1

    assert documents.delete(uploaded.id) is True
    assert documents.get(uploaded.id) is None
    assert documents.corpus_revision == 2
    assert rag.search("senal lunaria") == []
    assert database.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0
    assert database.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 0

    forgotten = agent.respond("Que indica la señal lunaria?")
    assert forgotten.abstained is True
    assert forgotten.grounded is False
    assert forgotten.reason == "no_current_evidence"
    assert forgotten.sources == []
