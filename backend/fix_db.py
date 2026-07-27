from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.models import Memory
from app.db.session import SessionLocal

def run():
    db = SessionLocal()
    memories = db.query(Memory).all()
    count = 0
    for memory in memories:
        changed = False
        if memory.memory_type == "insight":
            memory.memory_type = "principle"
            changed = True
        elif memory.memory_type == "architecture":
            memory.memory_type = "claim"
            changed = True
        
        if memory.epistemic_label == "Early User Acquisition":
            memory.epistemic_label = "framework"
            changed = True
        elif memory.epistemic_label == "Product Retention":
            memory.epistemic_label = "factual_claim"
            changed = True
        elif memory.epistemic_label == "Memory Engine":
            memory.epistemic_label = "factual_claim"
            changed = True
            
        if changed:
            count += 1
            
    db.commit()
    print(f"Updated {count} memories")

if __name__ == "__main__":
    run()
