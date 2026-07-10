from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Capture, Memory, MemoryRelation, Source
from app.services.relationship_service import QwenMemoryRelationDetector


class FakeRelationshipQwenClient:
    def __init__(self, *, source_memory_id: str, related_memory_id: str) -> None:
        self.source_memory_id = source_memory_id
        self.related_memory_id = related_memory_id
        self.calls = 0
        self.user_prompts: list[str] = []
        self.models: list[str | None] = []

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> dict:
        self.calls += 1
        self.user_prompts.append(user_prompt)
        self.models.append(model)
        return {
            "relationships": [
                {
                    "source_memory_id": self.source_memory_id,
                    "related_memory_id": self.related_memory_id,
                    "relationship_type": "tension",
                    "strength": "moderate",
                    "evidence_from_source": "Distribution cannot save a product",
                    "evidence_from_related": "test distribution channels early",
                    "explanation": "The new memory prioritizes product love while the older one prioritizes early distribution testing.",
                }
            ]
        }


def build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_relationship_detector_batches_and_skips_meta_memories() -> None:
    db = build_session()

    older_source = Source(source_type="text", title="Distribution note")
    db.add(older_source)
    db.flush()
    older_capture = Capture(source_id=older_source.id, inferred_intents=["remember"], status="ready")
    db.add(older_capture)
    db.flush()
    older_memory = Memory(
        source_id=older_source.id,
        capture_id=older_capture.id,
        memory_type="principle",
        epistemic_label="advice",
        content="Founders should test distribution channels early.",
        confidence="medium",
        source_strength="moderate",
        embedding_json=[0.7, 0.714142, 0.0],
    )
    db.add(older_memory)
    db.flush()

    new_source = Source(source_type="text", title="Product love note")
    db.add(new_source)
    db.flush()
    new_capture = Capture(source_id=new_source.id, inferred_intents=["question"], status="ready")
    db.add(new_capture)
    db.flush()
    product_memory = Memory(
        source_id=new_source.id,
        capture_id=new_capture.id,
        memory_type="warning",
        epistemic_label="advice",
        content="Distribution cannot save a product customers do not want.",
        confidence="medium",
        source_strength="moderate",
        embedding_json=[1.0, 0.0, 0.0],
    )
    intention_memory = Memory(
        source_id=new_source.id,
        capture_id=new_capture.id,
        memory_type="intention",
        epistemic_label="personal_reflection",
        content="Compare this with my older startup distribution notes.",
        confidence="high",
        source_strength="strong",
        embedding_json=[1.0, 0.0, 0.0],
    )
    question_memory = Memory(
        source_id=new_source.id,
        capture_id=new_capture.id,
        memory_type="question",
        epistemic_label="unresolved",
        content="How does this align with my older distribution advice?",
        confidence="high",
        source_strength="strong",
        embedding_json=[1.0, 0.0, 0.0],
    )
    db.add_all([product_memory, intention_memory, question_memory])
    db.flush()

    fake_client = FakeRelationshipQwenClient(
        source_memory_id=product_memory.id,
        related_memory_id=older_memory.id,
    )
    detector = QwenMemoryRelationDetector(client=fake_client)
    relations = detector.detect_for_memories(
        db=db,
        new_memories=[product_memory, intention_memory, question_memory],
    )

    assert fake_client.calls == 1
    assert fake_client.models == ["qwen-turbo"]
    assert len(relations) == 1
    assert relations[0].source_memory_id == product_memory.id
    assert relations[0].target_memory_id == older_memory.id
    assert relations[0].relation_type == "tension"
    assert product_memory.id in fake_client.user_prompts[0]
    assert intention_memory.id not in fake_client.user_prompts[0]
    assert question_memory.id not in fake_client.user_prompts[0]

    stored = db.query(MemoryRelation).all()
    assert len(stored) == 1
    db.close()


def test_relationship_detector_skips_loose_cross_domain_similarity() -> None:
    db = build_session()

    older_source = Source(source_type="text", title="FoundrGeeks")
    db.add(older_source)
    db.flush()
    older_capture = Capture(source_id=older_source.id, inferred_intents=["remember"], status="ready")
    db.add(older_capture)
    db.flush()
    older_memory = Memory(
        source_id=older_source.id,
        capture_id=older_capture.id,
        memory_type="principle",
        epistemic_label="framework",
        content="FoundrGeeks matches founders with potential teammates based on compatibility.",
        confidence="high",
        source_strength="moderate",
        embedding_json=[0.427033, 0.904236, 0.0],
    )
    db.add(older_memory)
    db.flush()

    new_source = Source(source_type="text", title="Ascentrade")
    db.add(new_source)
    db.flush()
    new_capture = Capture(source_id=new_source.id, inferred_intents=["reference"], status="ready")
    db.add(new_capture)
    db.flush()
    new_memory = Memory(
        source_id=new_source.id,
        capture_id=new_capture.id,
        memory_type="principle",
        epistemic_label="framework",
        content="Ascentrade lets traders copy another trader's trades.",
        confidence="high",
        source_strength="moderate",
        embedding_json=[1.0, 0.0, 0.0],
    )
    db.add(new_memory)
    db.flush()

    fake_client = FakeRelationshipQwenClient(
        source_memory_id=new_memory.id,
        related_memory_id=older_memory.id,
    )
    detector = QwenMemoryRelationDetector(client=fake_client)
    relations = detector.detect_for_memories(db=db, new_memories=[new_memory])

    assert relations == []
    assert fake_client.calls == 0
    assert db.query(MemoryRelation).count() == 0
    db.close()
