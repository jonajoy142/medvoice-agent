from app.db.base import Base
from app.db.session import get_engine
import app.models  # noqa: F401


def bootstrap_database() -> None:
    Base.metadata.create_all(bind=get_engine())
