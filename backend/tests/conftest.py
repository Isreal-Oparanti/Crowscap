import pytest
from app.services.recall_service import invalidate_recall_cache


@pytest.fixture(autouse=True)
def clean_recall_cache_for_tests():
    invalidate_recall_cache()
    yield
    invalidate_recall_cache()
