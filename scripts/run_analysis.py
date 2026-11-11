"""Run the full C4 analysis and write reports/results.json plus processed data.

All numbers in the README and executive summary render from results.json.
Revision statistics are computed on growth rates (100 x log difference of
the index) with the maturity restriction from the config: an observation
enters the revision sample only if its first vintage is at least
``maturity_vintages`` vintages before the final vintage, so its "latest"
value is close to settled.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from realtime_forecast.bridge import run_bridge_evaluation  # noqa: E402
from realtime_forecast.forecast import (  # noqa: E402
    block_bootstrap_gap,
    diebold_mariano,
    run_evaluation,
    score,
)
from realtime_forecast.revisions import (  # noqa: E402
    growth_revision_frame,
    noise_vs_news,
    revision_stats,
    revision_stats_by_phase,
    vintage_coverage,
)
from realtime_forecast.synthetic import make_synthetic_matrix  # noqa: E402
from realtime_forecast.vintages import load_rtdsm_matrix  # noqa: E402


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (pd.Period,)):
        return str(obj)
    return obj


def main() -> None:
    config = json.loads((ROOT / "configs/default.json").read_text())
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    matrices = {}
    results = {
        "generated_date_et": "2026-11-10",
        "target_vintage": config["target_vintage"],
        "indicators": {},
        "retail_sales": config["retail_sales"],
    }
    for key, cfg in config["indicators"].items():
        matrix = load_rtdsm_matrix(ROOT / "data/raw" / cfg["rtdsm_file"], cfg["freq"])
        matrices[key] = matrix
        freq = cfg["freq"]
        frame = growth_revision_frame(matrix, min_age_vintages=cfg["maturity_vintages"])
        stats = revision_stats(frame)
        by_phase = revision_stats_by_phase(frame)
        nn = noise_vs_news(frame, hac_lags=cfg["hac_lags"])
        stats["p90_abs_revision"] = float(
            frame["revision_latest_minus_first"].abs().quantile(0.90)
        )
        origins = [
            c
            for c in matrix.columns
            if pd.Period(cfg["eval_start_vintage"], freq=freq)
            <= c
            <= pd.Period(cfg["eval_end_vintage"], freq=freq)
        ]
        max_p = (
            config["ar"]["max_p_monthly"] if freq == "M" else config["ar"]["max_p_quarterly"]
        )
        min_train = (
            config["ar"]["min_train_monthly"]
            if freq == "M"
            else config["ar"]["min_train_quarterly"]
        )
        fc = run_evaluation(matrix, origins, max_p=max_p, min_train=min_train)
        fc.to_csv(processed / f"{key}_forecasts.csv", index=False)
        frame.assign(indicator=key).to_csv(processed / f"{key}_revisions.csv", index=False)
        matrix_out = matrix.copy()
        matrix_out.index = matrix_out.index.astype(str)
        matrix_out.columns = matrix_out.columns.astype(str)
        matrix_out.index.name = "observation_period"
        matrix_out.to_parquet(processed / f"{key}_vintage_matrix.parquet")
        evaluation = {
            "origin_window": [str(origins[0]), str(origins[-1])],
            "n_origins": int(len(fc)),
            "scores": score(fc),
            "diebold_mariano": diebold_mariano(fc),
            "bootstrap": block_bootstrap_gap(
                fc,
                block=cfg["bootstrap_block"],
                reps=config["bootstrap"]["reps"],
                seed=config["bootstrap"]["seed"],
            ),
        }
        results["indicators"][key] = {
            "label": cfg["label"],
            "originator": cfg["originator"],
            "alfred_series": cfg["alfred_series"],
            "freq": freq,
            "coverage": vintage_coverage(matrix),
            "revisions": {
                "maturity_vintages": cfg["maturity_vintages"],
                "stats": stats,
                "by_phase": by_phase,
                "noise_vs_news": nn,
            },
            "risk_band_pp": stats["p90_abs_revision"],
            "evaluation": evaluation,
        }
        print(f"{key}: revisions n={stats['n']}, eval origins={len(fc)}")

    bridge_cfg = config["bridge"]
    pce_origins = [
        c
        for c in matrices["pce"].columns
        if pd.Period(bridge_cfg["eval_start_vintage"], freq="Q")
        <= c
        <= pd.Period(bridge_cfg["eval_end_vintage"], freq="Q")
    ]
    bridge = run_bridge_evaluation(
        matrices["pce"],
        matrices["cpi"],
        matrices["ppi"],
        pce_origins,
        min_train=bridge_cfg["min_train_quarters"],
    )
    bridge.to_csv(processed / "pce_bridge_forecasts.csv", index=False)
    results["bridge"] = {
        "indicator": "pce",
        "origin_window": [str(pce_origins[0]), str(pce_origins[-1])],
        "n_origins": int(len(bridge)),
        "scores": score(bridge),
        "diebold_mariano": diebold_mariano(bridge),
        "bootstrap": block_bootstrap_gap(
            bridge, block=8, reps=config["bootstrap"]["reps"], seed=config["bootstrap"]["seed"]
        ),
    }
    print(f"bridge: origins={len(bridge)}")

    syn_matrix, planted = make_synthetic_matrix()
    syn_frame = growth_revision_frame(syn_matrix, min_age_vintages=24)
    syn_stats = revision_stats(syn_frame)
    results["synthetic_gate"] = {
        "planted_expected_mean_revision": planted["expected_mean_revision"],
        "recovered_mean_revision": syn_stats["mean_revision"],
        "planted_expected_mean_abs_revision": planted["expected_mean_abs_revision"],
        "recovered_mean_abs_revision": syn_stats["mean_abs_revision"],
        "n": syn_stats["n"],
    }
    print("synthetic gate:", results["synthetic_gate"])

    out = ROOT / "reports/results.json"
    out.write_text(json.dumps(_clean(results), indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
