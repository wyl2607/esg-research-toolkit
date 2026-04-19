from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from esg_frameworks.api import router as frameworks_router
from esg_frameworks.schemas import (
    FRAMEWORK_DISPLAY_NAMES,
    FRAMEWORK_VERSIONS,
)
from scripts.migrations.backfill_framework_versions import run


EXPECTED_CANONICAL_FRAMEWORK_VERSIONS = {
    "eu_taxonomy": "2020/852",
    "csrc_2023": "2023",
    "csrd": "ESRS-2024",
    "sec_climate": "SEC-2024",
    "gri_universal": "GRI-2021",
    "sasb_standards": "SASB-2023",
}

EXPECTED_CANONICAL_FRAMEWORK_DISPLAY_NAMES = {
    "eu_taxonomy": "EU Taxonomy",
    "csrc_2023": "China CSRC 2023",
    "csrd": "CSRD/ESRS",
    "sec_climate": "SEC Climate",
    "gri_universal": "GRI Universal",
    "sasb_standards": "SASB Standards",
}


def test_framework_versions_cover_supported_framework_ids() -> None:
    assert FRAMEWORK_VERSIONS == EXPECTED_CANONICAL_FRAMEWORK_VERSIONS
    assert FRAMEWORK_DISPLAY_NAMES == EXPECTED_CANONICAL_FRAMEWORK_DISPLAY_NAMES
    assert set(FRAMEWORK_VERSIONS) == set(FRAMEWORK_DISPLAY_NAMES)
    assert all(display_name for display_name in FRAMEWORK_DISPLAY_NAMES.values())
    assert all(version != "v1" for version in FRAMEWORK_VERSIONS.values())


def test_list_framework_versions_endpoint_returns_canonical_versions() -> None:
    app = FastAPI()
    app.include_router(frameworks_router)

    with TestClient(app) as client:
        response = client.get("/frameworks/versions")

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "framework_id": framework_id,
            "framework_version": framework_version,
            "display_name": FRAMEWORK_DISPLAY_NAMES[framework_id],
        }
        for framework_id, framework_version in FRAMEWORK_VERSIONS.items()
    ]
    assert all(
        set(item) == {"framework_id", "framework_version", "display_name"}
        for item in payload
    )


def test_backfill_framework_versions_updates_legacy_v1_rows() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE framework_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    framework_id TEXT NOT NULL,
                    framework_version TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO framework_analysis_results (framework_id, framework_version) VALUES "
                "(:framework_id_1, :framework_version_1), "
                "(:framework_id_2, :framework_version_2), "
                "(:framework_id_3, :framework_version_3), "
                "(:framework_id_4, :framework_version_4)"
            ),
            {
                "framework_id_1": "eu_taxonomy",
                "framework_version_1": "v1",
                "framework_id_2": "csrc_2023",
                "framework_version_2": "v1",
                "framework_id_3": "csrd",
                "framework_version_3": "ESRS-2024",
                "framework_id_4": "custom_framework",
                "framework_version_4": "v1",
            },
        )

    updated_rows = run(bind_engine=engine)

    assert updated_rows == 2

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT framework_id, framework_version FROM framework_analysis_results "
                "ORDER BY id"
            )
        ).all()

    assert rows == [
        ("eu_taxonomy", FRAMEWORK_VERSIONS["eu_taxonomy"]),
        ("csrc_2023", FRAMEWORK_VERSIONS["csrc_2023"]),
        ("csrd", "ESRS-2024"),
        ("custom_framework", "v1"),
    ]

    second_run_updated_rows = run(bind_engine=engine)
    assert second_run_updated_rows == 0
