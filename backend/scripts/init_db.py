from app.db.base import Base
from app.db.models import Capture, Memory, Source  # noqa: F401
from app.db.session import engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()

