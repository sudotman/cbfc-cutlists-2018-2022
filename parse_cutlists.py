import re
import json
from pathlib import Path
from typing import Dict, List, Optional

HEADER_RE = re.compile(r"Film Name\s*:\s*(?P<name>.+?)\s*(?:Links for more information|Language|$)", re.IGNORECASE)
DATE_RE = re.compile(r"Dated\s*(?P<date>\d{2}/\d{2}/\d{4})")
CERT_RE = re.compile(r"Cert\s*No\.\s*(?P<cert>[A-Z0-9/\-]+)", re.IGNORECASE)
LANG_RE = re.compile(r"Language\s*:\s*(?P<lang>[A-Za-z/ ]+)", re.IGNORECASE)


def flush_record(record: Dict, out_fh) -> None:
    """Write *record* as JSON line if it has a film_name."""
    if record.get("film_name"):
        json.dump(record, out_fh, ensure_ascii=False)
        out_fh.write("\n")


def parse_cutlists(src_path: Path, dest_path: Path) -> None:
    current: Dict[str, Optional[str] | List[str]] = {
        "film_name": None,
        "language": None,
        "certificate_no": None,
        "date": None,
        "cuts": [],  # type: ignore[list-item]
    }

    with src_path.open("r", encoding="utf-8", errors="ignore") as fh_in, dest_path.open("w", encoding="utf-8") as fh_out:
        for line in fh_in:
            header_m = HEADER_RE.search(line)
            if header_m:
                # flush previous film before starting a new one
                flush_record(current, fh_out)
                # reset
                current = {
                    "film_name": header_m.group("name").strip(),
                    "language": None,
                    "certificate_no": None,
                    "date": None,
                    "cuts": [],  # type: ignore[list-item]
                }
                # attempt to glean more info from the same line
                lang_m = LANG_RE.search(line)
                if lang_m:
                    current["language"] = lang_m.group("lang").strip()
                cert_m = CERT_RE.search(line)
                if cert_m:
                    current["certificate_no"] = cert_m.group("cert").strip()
                date_m = DATE_RE.search(line)
                if date_m:
                    current["date"] = date_m.group("date")
                continue  # go to next input line

            # for non-header lines, maybe pick up extra metadata
            if current["film_name"]:
                if current.get("language") is None:
                    lang_m = LANG_RE.search(line)
                    if lang_m:
                        current["language"] = lang_m.group("lang").strip()
                if current.get("certificate_no") is None:
                    cert_m = CERT_RE.search(line)
                    if cert_m:
                        current["certificate_no"] = cert_m.group("cert").strip()
                if current.get("date") is None:
                    date_m = DATE_RE.search(line)
                    if date_m:
                        current["date"] = date_m.group("date")

                # everything else add to cuts list
                current["cuts"].append(line.rstrip())

        # flush last record
        flush_record(current, fh_out)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse CBFC cutlists from OCR text into structured JSON lines.")
    parser.add_argument("ocr_txt", help="Path to the big OCR searchtext file")
    parser.add_argument("output", nargs="?", help="Output JSONL file (default: <input>.jsonl)")
    args = parser.parse_args()

    src = Path(args.ocr_txt)
    dest = Path(args.output) if args.output else src.with_suffix(".jsonl")
    parse_cutlists(src, dest)
    print(f"Written parsed records to {dest}")


if __name__ == "__main__":
    main() 