from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from report_parser.admin_routes import require_admin_token
from report_parser.disclosures_api import router as disclosures_router


@pytest.fixture
def disclosure_read_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session: Session = testing_session_local()

    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_admin_token] = lambda: None

    try:
        with TestClient(app) as client:
            yield client
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize("path", ["/disclosures/pending", "/disclosures/lane-stats"])
def test_disclosure_reads_require_admin_token(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    import main

    response = TestClient(main.app).get(path)

    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/disclosures/pending", "/disclosures/lane-stats"])
def test_authenticated_disclosure_reads_are_not_cacheable(
    disclosure_read_client: TestClient,
    path: str,
) -> None:
    response = disclosure_read_client.get(path)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
