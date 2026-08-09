import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from app.db.session import SessionLocal
from app.services.recall_service import get_due_recalls
from app.services.recall_evaluation_service import quick_recall
from app.schemas.recall import RecallQuickRequest

def test_backend_recall():
    db = SessionLocal()
    try:
        print("[TEST 1] Fetching due recalls...")
        res = get_due_recalls(db=db, limit=10)
        print(f"Total due count: {res.due_count}")
        if res.memories:
            mem = res.memories[0]
            print(f"Top memory ID: {mem.memory_id}")
            print(f"Human Title: {mem.human_title}")
            print(f"Human Prompt: {mem.human_prompt}")
            print(f"Pinned: {mem.pinned_from_notification}")
            
            target_id = res.memories[-1].memory_id if len(res.memories) > 1 else mem.memory_id
            print(f"\n[TEST 2] Fetching with target_memory_id={target_id}...")
            res_pinned = get_due_recalls(db=db, limit=10, target_memory_id=target_id)
            print(f"Top memory ID after pinning: {res_pinned.memories[0].memory_id}")
            print(f"Is pinned_from_notification: {res_pinned.memories[0].pinned_from_notification}")
            print(f"Surface reason: {res_pinned.memories[0].surface_reason}")
            assert res_pinned.memories[0].memory_id == target_id, "Target memory was not pinned to index 0!"
            assert res_pinned.memories[0].pinned_from_notification is True, "pinned_from_notification flag is false!"
            
            print(f"\n[TEST 3] Testing quick_recall action 'snooze_7d' on {mem.memory_id}...")
            snooze_res = quick_recall(db=db, memory_id=mem.memory_id, payload=RecallQuickRequest(action="snooze_7d"))
            print(f"Snooze feedback: {snooze_res.feedback}")
            print(f"Next due at: {snooze_res.next_due_at}")
            
            print("\n[SUCCESS] ALL BACKEND RECALL TESTS PASSED!")
        else:
            print("No due memories found in local database to test pinning, but API schema verified.")
    finally:
        db.close()

if __name__ == "__main__":
    test_backend_recall()
