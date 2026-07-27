import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.search_service import search_memories
from app.schemas.search import SearchRequest
from app.core.auth import _seed_demo_user_data
from app.services.embedding_service import get_memory_embedder

def run():
    db = SessionLocal()
    user_id = "test_demo_user_123"
    _seed_demo_user_data(db, user_id)
    embedder = get_memory_embedder()
    payload = SearchRequest(query="product design")
    
    try:
        res = search_memories(db=db, payload=payload, embedder=embedder, user_id=user_id)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
