from app.ai.structured_outputs import CaptureExtraction, ChatRoute, MemoryRelationshipBatch


def test_capture_extraction_normalizes_model_label_variants() -> None:
    extraction = CaptureExtraction.model_validate(
        {
            "source_title": "Product note",
            "inferred_intents": ["Compare", "watch-later"],
            "memories": [
                {
                    "memory_type": "Factual Claim",
                    "epistemic_label": "Personal Reflection",
                    "content": "A lovable product can create word of mouth.",
                    "summary": None,
                    "confidence": "Medium",
                    "confidence_reason": "The source states this directly but gives no cited evidence.",
                    "source_strength": "Moderate",
                }
            ],
        }
    )

    assert extraction.inferred_intents == ["compare", "watch_later"]
    assert extraction.memories[0].memory_type == "claim"
    assert extraction.memories[0].epistemic_label == "personal_reflection"
    assert extraction.memories[0].confidence == "medium"
    assert extraction.memories[0].source_strength == "moderate"


def test_memory_relationship_batch_normalizes_model_label_variants() -> None:
    batch = MemoryRelationshipBatch.model_validate(
        {
            "relationships": [
                {
                    "source_memory_id": "new-memory",
                    "related_memory_id": "old-memory",
                    "relationship_type": "Depends On Context",
                    "strength": "Strong",
                    "evidence_from_source": "product love",
                    "evidence_from_related": "distribution testing",
                    "explanation": "Both memories can be valid depending on the startup context.",
                }
            ]
        }
    )

    assert batch.relationships[0].relationship_type == "tension"
    assert batch.relationships[0].strength == "strong"


def test_capture_extraction_repairs_intention_used_as_epistemic_label() -> None:
    extraction = CaptureExtraction.model_validate(
        {
            "source_title": "FoundrGeeks",
            "inferred_intents": ["learned"],
            "memories": [
                {
                    "memory_type": "intention",
                    "epistemic_label": "intention",
                    "content": "The platform intends to connect compatible founders and skilled collaborators.",
                    "summary": "Connect compatible builders",
                    "confidence": "high",
                    "confidence_reason": "The product description states this platform goal directly.",
                    "source_strength": "moderate",
                }
            ],
        }
    )

    assert extraction.memories[0].memory_type == "intention"
    assert extraction.memories[0].epistemic_label == "personal_reflection"


def test_chat_route_normalizes_belief_audit_aliases() -> None:
    route = ChatRoute.model_validate(
        {
            "action": "evidence check",
            "reply": None,
            "reason": "The user asked to compare a belief against evidence.",
        }
    )

    assert route.action == "audit"
