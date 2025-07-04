import json
import sqlite3
from pathlib import Path
from typing import Dict, List

DB_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    film_name TEXT NOT NULL,
    language TEXT,
    certificate_no TEXT,
    cert_date TEXT,
    has_cuts INTEGER DEFAULT 0  -- 0 = submission only, 1 = has actual cuts
);

CREATE TABLE IF NOT EXISTS cuts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    film_id INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    cut_text TEXT NOT NULL
);

-- FTS5 index for fast full-text search over cut text + film name
CREATE VIRTUAL TABLE IF NOT EXISTS cuts_fts USING fts5(
    cut_text,
    film_name,
    content='cuts',
    content_rowid='id',
    tokenize='porter'
);

-- Keep FTS table in sync with cuts table
CREATE TRIGGER IF NOT EXISTS cuts_ai AFTER INSERT ON cuts BEGIN
    INSERT INTO cuts_fts(rowid, cut_text, film_name)
    VALUES (new.id, new.cut_text, (SELECT film_name FROM films WHERE id = new.film_id));
END;

CREATE TRIGGER IF NOT EXISTS cuts_ad AFTER DELETE ON cuts BEGIN
    INSERT INTO cuts_fts(cuts_fts, rowid, cut_text, film_name) VALUES('delete', old.id, NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS cuts_au AFTER UPDATE ON cuts BEGIN
    INSERT INTO cuts_fts(cuts_fts, rowid, cut_text, film_name) VALUES('delete', old.id, NULL, NULL);
    INSERT INTO cuts_fts(rowid, cut_text, film_name)
    VALUES (new.id, new.cut_text, (SELECT film_name FROM films WHERE id = new.film_id));
END;

-- Helpful indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_films_language ON films(language);
CREATE INDEX IF NOT EXISTS idx_films_year     ON films(substr(cert_date,-4));
CREATE INDEX IF NOT EXISTS idx_films_has_cuts ON films(has_cuts);
CREATE INDEX IF NOT EXISTS idx_films_name     ON films(film_name);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DB_SCHEMA_SQL)
    conn.commit()


def import_jsonl(jsonl_path: Path, conn: sqlite3.Connection) -> None:
    """Read *jsonl_path* and insert into DB.

    Each line has keys: film_name, language, certificate_no, date (cert_date), cuts (list[str])
    """
    cur = conn.cursor()

    film_cache: Dict[str, int] = {}

    with jsonl_path.open('r', encoding='utf-8') as fh:
        for line_no, raw in enumerate(fh, 1):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"Skip malformed JSONL line {line_no}: {exc}")
                continue

            film_name = record.get('film_name')
            if not film_name:
                continue

            film_id = film_cache.get(film_name)
            if film_id is None:
                # Determine if this record actually contains cut instructions (Applied Running Time marker)
                cuts: List[str] = record.get('cuts', [])
                has_cuts_flag = any('applied running time' in t.lower() for t in cuts)

                cur.execute(
                    "INSERT INTO films (film_name, language, certificate_no, cert_date, has_cuts) VALUES (?, ?, ?, ?, ?)",
                    (
                        film_name,
                        record.get('language'),
                        record.get('certificate_no'),
                        record.get('date'),
                        int(has_cuts_flag),
                    ),
                )
                film_id = cur.lastrowid
                film_cache[film_name] = film_id

            cuts: List[str] = record.get('cuts', [])
            to_insert = [(film_id, text) for text in cuts if text.strip()]
            cur.executemany("INSERT INTO cuts (film_id, cut_text) VALUES (?, ?)", to_insert)

    conn.commit()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create SQLite DB and populate with parsed CBFC cutlists.")
    parser.add_argument("jsonl", help="Path to JSONL produced by parse_cutlists.py")
    parser.add_argument("database", nargs="?", help="Output SQLite DB (default: cbfc_cutlists.db)")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    db_path = Path(args.database) if args.database else Path("cbfc_cutlists.db")

    # Create/connect DB and schema
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    # Import data
    import_jsonl(jsonl_path, conn)

    print(f"Imported data into {db_path}")


if __name__ == "__main__":
    main() 