# cbfc cutlists explorer
censorship isn't anything new to our country's film's certification body - yet this is an under-documented phenomena with not a lot of data easily accessible. you have to rely on RTI requests which can often take months to resolve properly. this is a chunk of 2018-2022 data that was scraped and OCR'd into a rough dataset. this dataset has been archived by the good folks at check [repository's data](#repository-data) below for more information


## hosted looks like this:
![demoScreenshot](static/demo.png)


## prerequisites

* python 3.9+
* preferably a virtualenv (recommended)
* optional: git (if you cloned the repo)
* internet access for first run (to pull the tiny `virtual-scroll-list` script from unpkg)

## quick start (windows powershell example)

```powershell
# 1. create and activate a virtual environment
python -m venv .venv
.venv\scripts\activate

# 2. install dependencies
pip install fastapi uvicorn pydantic anyio virtualenv

# 3. decompress the packaged ocr files (only the first time)
python decompress_gz.py data

## skip to step 5 if you don't wish to rebuild the database.

# 4.0. ensure you have all the data from the archive.org link below and place it in a sub-directory called "data"

# 4.1. parse the big ocr text into structured jsonl
python parse_cutlists.py "data/2018-2022 with letter_hocr_searchtext.txt" data/cutlists.jsonl

# 4.2. build the sqlite database (includes full-text index)
python init_db.py data/cutlists.jsonl cbfc_cutlists.db

# 5. launch everything (api + static ui)
python main.py                           # visit http://127.0.0.1:8000
python main.py --host 127.0.0.1 --port 9000  # custom host/port
python main.py --no-reload               # disable auto-reload (production)
```

## directory layout

```
static/          → single-page ui (plain html + tiny virtual list)
data/            → raw internet archive files (pdf, jp2, ocr, meta)
*.py             → utilities, api, importer
cbfc_cutlists.db → generated sqlite database (fts5 enabled)
```

## api endpoints (json)

| method | path                | description                                     |
|--------|---------------------|-------------------------------------------------|
| get    | /search?q=term      | full-text search inside individual cuts         |
| get    | /films              | paged list of films (filters: q, language, year, category) |
| get    | /films/{id}         | film detail + complete cut list                 |
| get    | /languages          | distinct languages in db                        |
| get    | /years              | distinct certification years                    |

examples:

```
# films with cuts in 2020
ajax → /films?category=cuts&year=2020

# full-text search for the word "violence"
ajax → /search?q=violence
```

## how the data flows

1. `decompress_gz.py` expands `*.gz` archives in `data/`
2. `parse_cutlists.py` streams the 20 mb ocr text and creates `data/cutlists.jsonl`
3. `init_db.py` creates the schema, populates it, sets `has_cuts` flag, builds fts5 index and useful sqlite indexes
4. `api.py` exposes the rest api + serves the static ui
5. `static/index.html` consumes the api, using `virtual-scroll-list` so the dom never contains more than ~100 rows (smooth scrolling)

## rebuilding after schema changes

if you edit the importer or add columns, delete the old db and repeat steps 5–6.

```powershell
remove-item cbfc_cutlists.db
python init_db.py data/cutlists.jsonl cbfc_cutlists.db
```

## troubleshooting

* **sqlite error "no such column has_cuts"** – you are using an old db. delete it and rebuild.
* **ui loads but searching fails** – ensure `main.py` is running and you are on http://127.0.0.1:8000 not the raw html file path.
* **large lists freeze** – make sure you pulled the latest `static/index.html` with the virtual list integration (hard refresh ctrl+f5).

## performance

the application has been optimized for fast query performance:

* **film filtering**: loading 10,000 films with cuts now takes **0.29ms** (previously 10-15 minutes)
* **cuts filtering**: uses precomputed `has_cuts` column instead of complex EXISTS queries
* **database size**: 20,043 films and 420,681 cuts
* **indexed queries**: proper sqlite indexing for film_id, language, year, and category
* **full-text search**: uses sqlite fts5 for fast cut content search
* **frontend performance**: virtual scrolling handles large result sets smoothly

if a film has "cuts" is done by this empirical filter of seeing if the title has "Applied Running Time" in it's title - seems to a good heuristic to filter out certificates vs data with cuts specified.

## repository data

the raw cbfc cut lists data is sourced from the internet archive:  
**source**: [central board of film certification cut lists 2018–2022](https://archive.org/details/cbfc-cutlists-2018-2022)

this repository contains cut lists issued by the central board of film certification from 2018 to the end of 2022, representing the pre-screening film censorship regime in india during that period. the original data is available under public domain mark 1.0.

## todo
- data is broken (due to the OCR dump not being accurate and being cut off sometimes) - this leads to page overflows, broken sentences etc - running it through a large ML model/LLM to sanitize this and "autocomplete" some of these could be very useful to the viatility of this project.
- incorporate a UI which is more appealing without sacrificing speed.
- host this on the web for easy access.

## license

all scripts in this repo © satyam kashyap. the raw cbfc documents are public record [available under RTI - but scraped from the internet]; verify local laws before redistribution. 