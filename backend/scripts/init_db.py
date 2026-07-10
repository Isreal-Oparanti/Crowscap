from app.core.config import get_settings
from app.db.models import Capture, Memory, MemoryRelation, Source  # noqa: F401
from app.db.schema import ensure_database_schema
from app.db.session import engine


def main() -> None:
    settings = get_settings()
    ensure_database_schema(engine=engine, database_url=settings.database_url)
    print("Database schema ready.")


if __name__ == "__main__":
    main()
