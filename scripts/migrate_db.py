#!/usr/bin/env python3
"""
DB 迁移脚本：为 company_reports 表添加合规所需列。
用法: python3 scripts/migrate_db.py [db_path]
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/esg_toolkit.db")

NEW_COLUMNS = [
    ("source_url",             "VARCHAR"),
    ("file_hash",              "VARCHAR"),
    ("downloaded_at",          "DATETIME"),
    ("deletion_requested",     "BOOLEAN NOT NULL DEFAULT 0"),
    ("deletion_requested_at",  "DATETIME"),
    ("updated_at",             "DATETIME"),
]

def get_existing_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(company_reports)").fetchall()
    return {r[1] for r in rows}

def migrate(db_path: Path) -> None:
    if not db_path.exists():
        print(f"❌ DB 不存在: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    existing = get_existing_columns(conn)
    added = []
    skipped = []

    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing:
            skipped.append(col_name)
        else:
            conn.execute(f"ALTER TABLE company_reports ADD COLUMN {col_name} {col_type}")
            added.append(col_name)

    conn.commit()
    conn.close()

    if added:
        print(f"✅ 已添加列：{', '.join(added)}")
    if skipped:
        print(f"ℹ️  已存在（跳过）：{', '.join(skipped)}")
    print("迁移完成。")

if __name__ == "__main__":
    migrate(DB_PATH)
