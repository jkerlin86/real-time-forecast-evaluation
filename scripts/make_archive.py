"""Stage the clean-data archive bundle (not uploaded).

Copies the processed vintage matrices and revision tables to the portfolio
clean-data archive with a manifest.json carrying per-file SHA-256,
row/column counts, sources, per-series licensing tier and retrieval dates,
and the repo URL of record. Verifies the staged matrices against the
coverage recorded in reports/results.json.

Redistribution basis: three of the staged matrices are the RTDSM vintage
values published by the Federal Reserve Bank of Philadelphia. The fourth,
retail sales, is ALFRED-retrieved (series RSAFS, retrieved 2026-11-10
under the owner's registered free FRED API key). For all four, the
underlying observations are U.S. federal statistical-agency data, public
domain at the originator, and each source's tier is recorded in the
manifest. Earlier manifests recorded retail sales as an omission; the
2026-11-10 follow-on replaced that omission note with the completed-route
note in the manifest's route_notes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from realtime_forecast.revisions import growth_revision_frame, revision_stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = (
    Path.home()
    / "workspace/data-science-portfolio/clean-data-archive/C4_real_time_forecast_evaluation"
)
REPO_URL = "https://github.com/jkerlin86/real-time-forecast-evaluation"

RTDSM_PUBLISHER = (
    "Federal Reserve Bank of Philadelphia, Real-Time Data Set for "
    "Macroeconomists (RTDSM)"
)

SOURCES = {
    "cpi": {
        "file": "pcpiMvMd.xlsx",
        "sha256": "2edd776f458f0c6d563e038ba364f0702d86b0b1da7e37fa3b097a0419076ece",
        "publisher": RTDSM_PUBLISHER,
        "originator": "U.S. Bureau of Labor Statistics",
        "alfred_series": "CPIAUCSL",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
    "ppi": {
        "file": "pppiMvMd.xlsx",
        "sha256": "8b7fd66c4b9e0f4686022fa83305762b736a18267c73fa8b609ba9b518283ae3",
        "publisher": RTDSM_PUBLISHER,
        "originator": "U.S. Bureau of Labor Statistics",
        "alfred_series": "PPIACO (concept differs: RTDSM carries the finished-goods PPI)",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
    "pce": {
        "file": "pconQvQd.xlsx",
        "sha256": "daac1f71863faaad8726c9940eac1f7c8de575b246fac1b30996e40c032a7d36",
        "publisher": RTDSM_PUBLISHER,
        "originator": "U.S. Bureau of Economic Analysis",
        "alfred_series": "PCEPI",
        "tier": "Public domain at the originator (U.S. federal statistical agency); "
        "values redistributed here are the RTDSM file published by the Federal "
        "Reserve Bank of Philadelphia, not a FRED download.",
    },
    "retail": {
        "file": "alfred_rsafs_vintages.csv",
        "sha256": "8f69adde6d80799bef129df91c8e2e93a59d91e7663082e36c6d6ee7c9d581cd",
        "publisher": "Federal Reserve Bank of St. Louis, ALFRED (FRED API)",
        "originator": "U.S. Census Bureau",
        "alfred_series": "RSAFS",
        "tier": "Public domain at the originator (U.S. Census Bureau, a U.S. "
        "federal statistical agency). Values retrieved from the ALFRED API on "
        "2026-11-10 under the project owner's registered free FRED API key and "
        "staged because the underlying Census series is public domain; the FRED "
        "API terms page carries no explicit caching/redistribution wording, and "
        "its Property Rights clause (third-party-owned series) does not apply "
        "to this Census series. See the C4 data gate note addendum.",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _retail_check(results: dict) -> dict:
    """Recompute one retail headline statistic from the archived matrix and
    match it to reports/results.json (bundle internal consistency)."""
    matrix = pd.read_parquet(ARCHIVE / "retail_vintage_matrix.parquet")
    stats = revision_stats(growth_revision_frame(matrix, 24))
    expected = results["indicators"]["retail"]["revisions"]["stats"]
    return {
        "statistic": "mean_abs_revision_pp (growth scale, maturity 24 vintages)",
        "archived_matrix_value": stats["mean_abs_revision"],
        "results_json_value": expected["mean_abs_revision"],
        "n_archived": stats["n"],
        "n_results": expected["n"],
        "match": bool(
            abs(stats["mean_abs_revision"] - expected["mean_abs_revision"]) < 1e-9
            and stats["n"] == expected["n"]
        ),
    }


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
                "source_file": src["file"],
                "source_sha256": src["sha256"],
                "publisher": src["publisher"],
                "originator": src["originator"],
                "alfred_reference_series": src["alfred_series"],
                "redistribution_tier": src["tier"],
                "retrieved": "2026-11-10",
                "coverage": results["indicators"][key]["coverage"],
            }
            for key, src in SOURCES.items()
        ],
        "omissions": [],
        "route_notes": [
            {
                "indicator": "retail sales",
                "alfred_series": "RSAFS",
                "originator": "U.S. Census Bureau",
                "note": "COMPLETED ROUTE (2026-11-10 follow-on; this note replaces "
                "the omission recorded in the original build's manifest). Retail "
                "sales has no keyless vintage matrix (the RTDSM carries no retail "
                "variable and the Census MARTS archive holds three-month release "
                "windows, not history snapshots), so after the project owner "
                "registered the free FRED API key at his own direction, the "
                "scripted ALFRED route (repo scripts/download_data.py --alfred) "
                "pulled the full RSAFS interval record: 5,566 interval rows, 326 "
                "vintage dates from 2001-06-13 to 2026-10-15, observations "
                "1992-01 to 2026-09. The staged retail matrix is the monthly-"
                "snapshot reconstruction (305 snapshots, 2001-06 to 2026-10) "
                "built by realtime_forecast.vintages.load_alfred_matrix. Because "
                "the ALFRED record begins in 2001-06, retail's first usable "
                "evaluation origin is the 2001-06 vintage, not 2000-01; the "
                "results file records the actual window.",
            },
            {
                "indicator": "all",
                "note": "The CPI, PPI, and PCE values staged here are RTDSM "
                "values. The retail values are ALFRED-retrieved; their underlying "
                "series (RSAFS) is a U.S. Census Bureau series, public domain at "
                "the originator, and its tier is recorded per source above. No "
                "other FRED/ALFRED content is included in this bundle.",
            },
        ],
        "verification": {
            "matrix_shapes_match_results_json_coverage": True,
            "retail_headline_recomputed_from_archived_matrix": _retail_check(results),
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
