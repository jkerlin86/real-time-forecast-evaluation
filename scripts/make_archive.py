"""Stage the clean-data archive bundle (not uploaded).

Copies the processed vintage matrices and revision tables to the portfolio
clean-data archive with a manifest.json carrying per-file SHA-256,
row/column counts, sources, per-series licensing tier and retrieval dates,
and the repo URL of record. Verifies the staged matrices against the
coverage recorded in reports/results.json.

Redistribution basis: the values staged are the RTDSM vintage values
published by the Federal Reserve Bank of Philadelphia; the underlying
observations are U.S. federal statistical-agency data, public domain at
the originator. No FRED/ALFRED values are staged (none were used). The
fourth indicator, retail sales, has no vintage values to stage; the
manifest records the omission and its reason.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = (
    Path.home()
    / "workspace/data-science-portfolio/clean-data-archive/C4_real_time_forecast_evaluation"
)
REPO_URL = "https://github.com/jkerlin86/real-time-forecast-evaluation"

SOURCES = {
    "cpi": {
        "file": "pcpiMvMd.xlsx",
        "sha256": "2edd776f458f0c6d563e038ba364f0702d86b0b1da7e37fa3b097a0419076ece",
        "originator": "U.S. Bureau of Labor Statistics",
        "alfred_series": "CPIAUCSL",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
    "ppi": {
        "file": "pppiMvMd.xlsx",
        "sha256": "8b7fd66c4b9e0f4686022fa83305762b736a18267c73fa8b609ba9b518283ae3",
        "originator": "U.S. Bureau of Labor Statistics",
        "alfred_series": "PPIACO (concept differs: RTDSM carries the finished-goods PPI)",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
    "pce": {
        "file": "pconQvQd.xlsx",
        "sha256": "daac1f71863faaad8726c9940eac1f7c8de575b246fac1b30996e40c032a7d36",
        "originator": "U.S. Bureau of Economic Analysis",
        "alfred_series": "PCEPI",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    results = json.loads((ROOT / "reports/results.json").read_text())
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    files = []
    for key, src in SOURCES.items():
        staged = ARCHIVE / f"{key}_vintage_matrix.parquet"
        shutil.copyfile(ROOT / f"data/processed/{key}_vintage_matrix.parquet", staged)
        df = pd.read_parquet(staged)
        cov = results["indicators"][key]["coverage"]
        assert df.shape == (cov["n_observations"], cov["n_vintages"]), key
        files.append(
            {
                "file": staged.name,
                "sha256": sha256(staged),
                "bytes": staged.stat().st_size,
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
                "content": "vintage matrix: rows are observation periods, columns are "
                "vintage periods, cells are the index value as published in that vintage",
            }
        )
        rev = ARCHIVE / f"{key}_revision_table.csv"
        shutil.copyfile(ROOT / f"data/processed/{key}_revisions.csv", rev)
        rdf = pd.read_csv(rev)
        files.append(
            {
                "file": rev.name,
                "sha256": sha256(rev),
                "bytes": rev.stat().st_size,
                "rows": int(len(rdf)),
                "columns": int(len(rdf.columns)),
                "content": "derived revision table on the growth scale, "
                "maturity-restricted (first release, latest, revision)",
            }
        )
    manifest = {
        "project": "C4, The Revision Is the Story: A Real-Time Forecast Evaluation "
        "with ALFRED Vintages (roadmap Project 6)",
        "repo_url": REPO_URL,
        "generated_date_et": "2026-11-10",
        "files": files,
        "sources": [
            {
                "indicator": key,
                "rtdsm_file": src["file"],
                "rtdsm_sha256": src["sha256"],
                "publisher": "Federal Reserve Bank of Philadelphia, Real-Time Data "
                "Set for Macroeconomists (RTDSM)",
                "originator": src["originator"],
                "alfred_reference_series": src["alfred_series"],
                "redistribution_tier": src["tier"],
                "retrieved": "2026-11-10",
                "coverage": results["indicators"][key]["coverage"],
            }
            for key, src in SOURCES.items()
        ],
        "omissions": [
            {
                "indicator": "retail sales",
                "alfred_series": "RSAFS",
                "originator": "U.S. Census Bureau",
                "note": "No vintage values are staged for retail sales because no "
                "keyless vintage matrix exists (the RTDSM carries no retail "
                "variable and the Census MARTS archive holds three-month release "
                "windows, not history snapshots). The ALFRED API route in the "
                "repo's scripts/download_data.py builds the matrix when a reader "
                "supplies a free FRED API key. See the C4 data gate note.",
            },
            {
                "indicator": "all",
                "note": "No FRED/ALFRED values are included anywhere in this bundle. "
                "FRED terms prohibit caching/archiving FRED content for third-party "
                "provision; the staged values are RTDSM values, as recorded per "
                "source above.",
            },
        ],
        "verification": {
            "matrix_shapes_match_results_json_coverage": True,
            "headline": {
                key: {
                    "mean_abs_revision_pp": results["indicators"][key]["revisions"]["stats"][
                        "mean_abs_revision"
                    ],
                    "risk_band_pp": results["indicators"][key]["risk_band_pp"],
                    "rmse_gap_naive_minus_realtime": results["indicators"][key]["evaluation"][
                        "scores"
                    ]["rmse_gap_naive_minus_realtime"],
                }
                for key in SOURCES
            },
        },
    }
    (ARCHIVE / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(f["bytes"] for f in files) + (ARCHIVE / "manifest.json").stat().st_size
    print(f"archive staged at {ARCHIVE}: {len(files)} data files, total {total} bytes")


if __name__ == "__main__":
    main()
