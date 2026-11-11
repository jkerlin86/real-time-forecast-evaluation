"""Download the vintage matrices used by this project.

Primary route (keyless, used for the published results): the Real-Time Data
Set for Macroeconomists (RTDSM) of the Federal Reserve Bank of
Philadelphia, media-library XLSX files:

- pcpiMvMd.xlsx  (CPI, monthly vintages)
- pppiMvMd.xlsx  (PPI finished goods, monthly vintages)
- pconQvQd.xlsx  (PCE price index, quarterly vintages)

Secondary route (requires the reader's own free FRED API key, read from the
FRED_API_KEY environment variable; never commit a key): the ALFRED API
vintage endpoints. This route is what adds the fourth indicator, retail
sales (RSAFS), whose vintage matrix has no keyless source. It writes
long-format vintage observations for any listed series.

Licensing note: FRED's terms bar caching/archiving FRED content for
third-party provision and ML-training use; the keyed route is for the
reader's own analysis. The RTDSM files are published by the Federal
Reserve Bank of Philadelphia for research use with citation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RTDSM_FILES = {
    "pcpiMvMd.xlsx": "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/pcpiMvMd.xlsx?sc_lang=en&hash=E41A743DC6423F950B10C3DE7A4F674D",
    "pppiMvMd.xlsx": "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/pppiMvMd.xlsx?sc_lang=en&hash=D9C0D4D0B10B4BAD222AC0526EB5D9AD",
    "pconQvQd.xlsx": "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/pconQvQd.xlsx?sc_lang=en&hash=846BC4E9E2C9986E7A1A5268440E0F82",
}

ALFRED_SERIES = ["CPIAUCSL", "PPIACO", "RSAFS", "PCEPI"]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers = {"User-Agent": "Mozilla/5.0"}
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=2)))
    return s


def download_rtdsm(raw_dir: str) -> dict:
    os.makedirs(raw_dir, exist_ok=True)
    s = _session()
    manifest = {}
    for name, url in RTDSM_FILES.items():
        path = os.path.join(raw_dir, name)
        if os.path.exists(path):
            print(f"exists, skipping: {name}")
        else:
            r = s.get(url, timeout=120)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"downloaded: {name} ({len(r.content)} bytes)")
        with open(path, "rb") as f:
            manifest[name] = hashlib.sha256(f.read()).hexdigest()
    return manifest


def download_alfred(raw_dir: str, api_key: str) -> None:
    """Fetch ALFRED vintage observations for the four series (long format).

    Uses the FRED API series/observations endpoint with vintage dates:
    first the list of vintage dates, then one request per vintage is
    avoided by using output=1 (all vintages in one response) where the API
    supports it. Writes one CSV per series: date, vintage_date, value.
    """
    import csv

    base = "https://api.stlouisfed.org/fred/series/observations"
    s = _session()
    for series in ALFRED_SERIES:
        params = {
            "series_id": series,
            "api_key": api_key,
            "file_type": "json",
            "output": 1,
        }
        r = s.get(base, params=params, timeout=120)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("observations", [])
        path = os.path.join(raw_dir, f"alfred_{series.lower()}_vintages.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "vintage_date", "value"])
            for obs in rows:
                w.writerow([obs["date"], obs.get("vintage_date", ""), obs["value"]])
        print(f"alfred {series}: {len(rows)} vintage observations -> {path}")
        time.sleep(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument(
        "--alfred",
        action="store_true",
        help="also fetch ALFRED vintages (requires FRED_API_KEY in the environment)",
    )
    args = ap.parse_args()
    manifest = download_rtdsm(args.raw_dir)
    print(json.dumps({"rtdsm_sha256": manifest}, indent=2))
    if args.alfred:
        key = os.environ.get("FRED_API_KEY", "")
        if not key:
            raise SystemExit("FRED_API_KEY is not set; skipping the ALFRED route.")
        download_alfred(args.raw_dir, key)


if __name__ == "__main__":
    main()
