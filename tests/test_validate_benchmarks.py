import json
import sqlite3
from pathlib import Path

from scripts import validate_benchmarks


def _create_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE industry_benchmarks (
                id INTEGER PRIMARY KEY,
                industry_code TEXT,
                metric_name TEXT,
                period_year INTEGER,
                p10 REAL,
                p25 REAL,
                p50 REAL,
                p75 REAL,
                p90 REAL,
                sample_size REAL
            )
            """
        )
        conn.commit()


def test_validate_benchmarks_pass_case(tmp_path, capsys) -> None:
    db_path = tmp_path / "ok.db"
    _create_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO industry_benchmarks (
                industry_code, metric_name, period_year,
                p10, p25, p50, p75, p90, sample_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("D35.11", "scope1_co2e_tonnes", 2024, 10.0, 20.0, 30.0, 40.0, 50.0, 3),
        )
        conn.commit()

    exit_code = validate_benchmarks.main(["--db", str(db_path)])

    assert exit_code == 0
    output_lines = capsys.readouterr().out.strip().splitlines()
    assert len(output_lines) == 1
    assert output_lines[0].startswith("SUMMARY ")

    summary = json.loads(output_lines[0][len("SUMMARY ") :])
    assert summary["status"] == "ok"
    assert summary["rows_checked"] == 1
    assert summary["violations"] == 0


def test_validate_benchmarks_fail_case(tmp_path, capsys) -> None:
    db_path = tmp_path / "bad.db"
    _create_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO industry_benchmarks (
                industry_code, metric_name, period_year,
                p10, p25, p50, p75, p90, sample_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("D35.11", "scope1_co2e_tonnes", 2024, 10.0, 30.0, 20.0, 40.0, 50.0, 0),
                ("C20.14", "water_withdrawal_m3", 2024, float("nan"), 2.0, 3.0, 4.0, float("inf"), float("inf")),
            ],
        )
        conn.commit()

    exit_code = validate_benchmarks.main(["--db", str(db_path)])

    assert exit_code == 1
    output_lines = capsys.readouterr().out.strip().splitlines()
    assert len(output_lines) == 3

    summary = json.loads(output_lines[0][len("SUMMARY ") :])
    assert summary["status"] == "violations"
    assert summary["rows_checked"] == 2
    assert summary["violations"] == 2

    first_violation = json.loads(output_lines[1][len("VIOLATION ") :])
    second_violation = json.loads(output_lines[2][len("VIOLATION ") :])

    assert "sample_size_lt_1" in first_violation["issues"]
    assert "percentile_order_invalid" in first_violation["issues"]

    assert any(issue in second_violation["issues"] for issue in ("p10_not_finite", "p10_not_numeric"))
    assert "p90_not_finite" in second_violation["issues"]
    assert "sample_size_not_finite" in second_violation["issues"]
