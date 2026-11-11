"""Figures for the C4 report, drawn from the processed revision/forecast
frames and reports/results.json. All values come from the pipeline outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

ORDER = ["cpi", "ppi", "pce"]
TITLES = {"cpi": "CPI", "ppi": "PPI (finished goods)", "pce": "PCE prices"}


def main() -> None:
    results = json.loads((ROOT / "reports/results.json").read_text())
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)

    # 1. Revision distributions
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharex=False)
    for ax, key in zip(axes, ORDER, strict=True):
        frame = pd.read_csv(ROOT / f"data/processed/{key}_revisions.csv")
        rev = frame["revision_latest_minus_first"].to_numpy()
        ax.hist(rev, bins=41, color="#30506e", alpha=0.85)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_title(f"{TITLES[key]} (n={len(rev)})")
        ax.set_xlabel("Revision of growth, pp (latest minus first)")
    axes[0].set_ylabel("Observations")
    fig.tight_layout()
    fig.savefig(figdir / "fig_revision_distributions.png", dpi=150)
    plt.close(fig)

    # 2. Mean absolute revision by cycle phase
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(len(ORDER))
    width = 0.36
    for i, phase in enumerate(["expansion", "contraction"]):
        vals = []
        for key in ORDER:
            st = results["indicators"][key]["revisions"]["by_phase"][phase]
            vals.append(st["mean_abs_revision"] if st.get("reported") else np.nan)
        ax.bar(x + (i - 0.5) * width, vals, width, label=phase.capitalize())
    ax.set_xticks(x, [TITLES[k] for k in ORDER])
    ax.set_ylabel("Mean absolute revision, pp")
    ax.set_title("Revision size by NBER cycle phase (reported phases only)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figdir / "fig_revision_by_phase.png", dpi=150)
    plt.close(fig)

    # 3. Honest vs naive RMSE (AR arms + PCE bridge)
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    labels = ["CPI AR", "PPI AR", "PCE AR", "PCE bridge"]
    rt = [results["indicators"][k]["evaluation"]["scores"]["realtime_rmse"] for k in ORDER]
    rt.append(results["bridge"]["scores"]["realtime_rmse"])
    nv = [results["indicators"][k]["evaluation"]["scores"]["naive_rmse"] for k in ORDER]
    nv.append(results["bridge"]["scores"]["naive_rmse"])
    x = np.arange(len(labels))
    ax.bar(x - 0.19, rt, 0.38, label="Real-time (honest)", color="#b0562f")
    ax.bar(x + 0.19, nv, 0.38, label="Final data (naive)", color="#30506e")
    ax.set_xticks(x, labels)
    ax.set_ylabel("RMSE vs latest-vintage actual, pp")
    ax.set_title("The same benchmark, evaluated honestly and naively")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figdir / "fig_honest_vs_naive.png", dpi=150)
    plt.close(fig)

    # 4. Cumulative squared-error difference, CPI (naive minus real-time)
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    fc = pd.read_csv(ROOT / "data/processed/cpi_forecasts.csv")
    d = fc["naive_error"] ** 2 - fc["realtime_error"] ** 2
    ax.plot(np.cumsum(d), color="#30506e")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Forecast origin (2000-01 to 2025-12 vintages, in order)")
    ax.set_ylabel("Cumulative squared-error difference")
    ax.set_title("CPI: cumulative loss differential (negative = final data flatters)")
    fig.tight_layout()
    fig.savefig(figdir / "fig_cpi_cumulative_loss_diff.png", dpi=150)
    plt.close(fig)

    print("figures written to", figdir)


if __name__ == "__main__":
    main()
