from pathlib import Path
import sqlite3
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

DB_PATH = Path("cbfc_cutlists.db")

app = FastAPI(title="CBFC Cutlists API", version="0.1")

# CORS (allow any origin so the UI can be served from different port if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static front-end (index.html + JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access by name
    return conn


class FilmBase(BaseModel):
    id: int
    film_name: str
    language: Optional[str] = None
    certificate_no: Optional[str] = None
    cert_date: Optional[str] = None


class FilmOut(FilmBase):
    has_cuts: bool


# Keep alias for compatibility
Film = FilmOut


class Cut(BaseModel):
    id: int
    cut_text: str


class FilmDetail(FilmBase):
    cuts: List[Cut]


@app.get("/films/{film_id}", response_model=FilmDetail)
def film_detail(film_id: int):
    conn = get_conn()
    cur = conn.cursor()

    film_row = cur.execute("SELECT * FROM films WHERE id = ?", (film_id,)).fetchone()
    if film_row is None:
        raise HTTPException(status_code=404, detail="Film not found")

    cut_rows = cur.execute("SELECT id, cut_text FROM cuts WHERE film_id = ? ORDER BY id", (film_id,)).fetchall()
    conn.close()

    film = FilmDetail(
        id=film_row["id"],
        film_name=film_row["film_name"],
        language=film_row["language"],
        certificate_no=film_row["certificate_no"],
        cert_date=film_row["cert_date"],
        cuts=[Cut(id=r["id"], cut_text=r["cut_text"]) for r in cut_rows],
    )
    return film


class SearchResult(BaseModel):
    film_id: int
    film_name: str
    snippet: str


@app.get("/search", response_model=List[SearchResult])
def search(
    q: str = Query(..., description="Search term"),
    limit: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None),
):
    conn = get_conn()
    cur = conn.cursor()

    sql = (
        "SELECT cuts.id AS cut_id, films.id AS film_id, films.film_name, cuts.cut_text AS full_text "
        "FROM cuts_fts "
        "JOIN cuts ON cuts_fts.rowid = cuts.id "
        "JOIN films ON cuts.film_id = films.id "
        "WHERE cuts_fts MATCH ? "
    )
    params = [q]

    if language:
        sql += "AND films.language = ? "
        params.append(language)

    sql += "LIMIT ?"
    params.append(limit)

    try:
        rows = cur.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid search syntax: {exc}")

    conn.close()

    def make_snippet(text: str, term: str, radius: int = 60) -> str:
        lower = text.lower()
        term_lower = term.lower()
        idx = lower.find(term_lower)
        if idx == -1:
            return text[:2 * radius] + ("…" if len(text) > 2 * radius else "")
        start = max(0, idx - radius)
        end = min(len(text), idx + len(term) + radius)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        snippet = text[start:end]
        # simple highlight (case-insensitive replace first occurrence)
        snippet_lower = snippet.lower()
        rel_idx = snippet_lower.find(term_lower)
        if rel_idx != -1:
            snippet = (
                snippet[:rel_idx]
                + "<b>"
                + snippet[rel_idx : rel_idx + len(term)]
                + "</b>"
                + snippet[rel_idx + len(term) :]
            )
        return prefix + snippet + suffix

    results = []
    for r in rows:
        snippet = make_snippet(r["full_text"], q)
        results.append(SearchResult(film_id=r["film_id"], film_name=r["film_name"], snippet=snippet))

    return results


@app.get("/films", response_model=List[FilmOut])
def list_films(
    language: Optional[str] = Query(None),  # Keep for backward compatibility
    languages: Optional[List[str]] = Query(None, description="Multiple languages to filter by"),
    q: Optional[str] = Query(None, description="Case-insensitive substring match on film name"),
    category: Optional[str] = Query(None, pattern="^(cuts|others)$", description="films with/without cuts"),
    year: Optional[str] = Query(None, description="Filter by certification year, e.g., '2022'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
):
    conn = get_conn()
    cur = conn.cursor()

    # Modified SQL to include has_cuts calculation based on "Applied Running Time"
    sql = """
    SELECT films.*, 
           EXISTS (SELECT 1 FROM cuts WHERE film_id = films.id AND LOWER(cut_text) LIKE '%applied running time%') as has_cuts 
    FROM films 
    """
    clauses = []
    params = []
    
    # Handle multiple languages (new parameter takes priority)
    selected_languages = languages if languages else ([language] if language else [])
    if selected_languages:
        placeholders = ','.join(['?' for _ in selected_languages])
        clauses.append(f"language IN ({placeholders})")
        params.extend(selected_languages)
    
    if q:
        clauses.append("film_name LIKE ?")
        params.append(f"%{q}%")

    cuts_subquery = "EXISTS (SELECT 1 FROM cuts WHERE film_id = films.id AND LOWER(cut_text) LIKE '%applied running time%')"
    if category == "cuts":
        clauses.append(cuts_subquery)
    elif category == "others":
        clauses.append(f"NOT {cuts_subquery}")

    if year:
        clauses.append("SUBSTR(cert_date, -4) = ?")
        params.append(year)

    if clauses:
        sql += "WHERE " + " AND ".join(clauses) + " "

    sql += "ORDER BY film_name COLLATE NOCASE LIMIT ? OFFSET ?"
    params.extend([limit, skip])

    rows = cur.execute(sql, params).fetchall()
    conn.close()

    return [FilmOut(**dict(r)) for r in rows]


# Distinct languages helper endpoint
@app.get("/languages", response_model=List[str])
def languages():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT language FROM films WHERE language IS NOT NULL ORDER BY language").fetchall()
    conn.close()
    return [r["language"] for r in rows if r["language"]]


@app.get("/years", response_model=List[str])
def years():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT SUBSTR(cert_date, -4) as year FROM films WHERE year IS NOT NULL ORDER BY year DESC").fetchall()
    conn.close()
    return [r["year"] for r in rows if r["year"]]


# Serve the SPA index at root without blocking other API paths
@app.get("/")
def index():
    return FileResponse("static/index.html")


# To run: `uvicorn api:app --reload` 