from sqlalchemy import text
from app.db.session import SessionLocal

def merge_duplicate_users():
    db = SessionLocal()
    try:
        # Find emails with multiple user records
        emails_query = text("""
            SELECT email, COUNT(*) as count 
            FROM users 
            GROUP BY email 
            HAVING COUNT(*) > 1
        """)
        results = db.execute(emails_query).fetchall()
        print(f"Found {len(results)} emails with duplicate accounts.")

        for row in results:
            email = row[0]
            # Fetch all user IDs for this email
            users = db.execute(
                text("SELECT id, name, created_at FROM users WHERE email = :email ORDER BY created_at ASC"),
                {"email": email}
            ).fetchall()

            if not users or len(users) < 2:
                continue

            # Primary user is the first one or the one starting with 'g_' or has data
            primary_id = users[0][0]
            secondary_ids = [u[0] for u in users[1:]]

            print(f"Merging {email}: Primary={primary_id}, Secondaries={secondary_ids}")

            for sec_id in secondary_ids:
                db.execute(text("UPDATE memories SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE sources SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE captures SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE conversations SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE chat_messages SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE reminders SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE recall_reviews SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("UPDATE user_preferences SET user_id = :p_id WHERE user_id = :s_id"), {"p_id": primary_id, "s_id": sec_id})
                db.execute(text("DELETE FROM users WHERE id = :s_id"), {"s_id": sec_id})

            db.commit()
            print(f"Successfully merged duplicate accounts for {email} into primary ID {primary_id}!")

    except Exception as e:
        db.rollback()
        print(f"Error merging duplicate users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    merge_duplicate_users()
