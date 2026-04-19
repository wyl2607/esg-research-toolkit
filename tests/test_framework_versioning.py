from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from esg_frameworks.api import router as frameworks_router
from esg_frameworks.schemas import FrameworkScoreResult
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
        conn.execute(
            text(
                "INSERT INTO framework_analysis_results (framework_id, framework_version) "
                "VALUES (:framework_id, :framework_version)"
            ),
            {"framework_id": "sasb_standards", "framework_version": " V1 "},
        )

    updated_rows = run(bind_engine=engine)

    assert updated_rows == 3

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
        ("sasb_standards", FRAMEWORK_VERSIONS["sasb_standards"]),
    ]

    second_run_updated_rows = run(bind_engine=engine)
    assert second_run_updated_rows == 0


def test_backfill_framework_versions_skips_rows_that_would_hit_unique_conflict() -> None:
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
                    company_name TEXT NOT NULL,
                    report_year INTEGER NOT NULL,
                    framework_id TEXT NOT NULL,
                    framework_version TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    UNIQUE (company_name, report_year, framework_id, framework_version, payload_hash)
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO framework_analysis_results "
                "(company_name, report_year, framework_id, framework_version, payload_hash) VALUES "
                "(:company, :year, :framework_id, :legacy_version, :payload_hash), "
                "(:company, :year, :framework_id, :canonical_version, :payload_hash)"
            ),
            {
                "company": "BMW AG",
                "year": 2024,
                "framework_id": "eu_taxonomy",
                "legacy_version": "v1",
                "canonical_version": FRAMEWORK_VERSIONS["eu_taxonomy"],
                "payload_hash": "same-hash",
            },
        )

    updated_rows = run(bind_engine=engine)
    assert updated_rows == 0

    with engine.connect() as conn:
        versions = conn.execute(
            text(
                "SELECT framework_version FROM framework_analysis_results "
                "ORDER BY framework_version"
            )
        ).scalars().all()
    assert versions == [FRAMEWORK_VERSIONS["eu_taxonomy"], "v1"]


def test_framework_score_result_normalizes_uppercase_legacy_version() -> None:
    result = FrameworkScoreResult(
        framework="EU Taxonomy",
        framework_id="eu_taxonomy",
        framework_region="EU",
        company_name="BMW AG",
        report_year=2024,
        framework_version=" V1 ",
        total_score=0.8,
        grade="B",
        dimensions=[],
        gaps=[],
        recommendations=[],
        coverage_pct=90.0,
    )
    assert result.framework_version == FRAMEWORK_VERSIONS["eu_taxonomy"]
