"""Build the two analysis notebooks (unexecuted). Execute with
scripts/execute_notebooks.py. Notebooks read the package and the raw data
files directly, so every number they show is recomputed, not copied.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

SETUP = """import sys
sys.path.insert(0, "../src")
import pandas as pd
from realtime_forecast.vintages import load_alfred_matrix, load_rtdsm_matrix
from realtime_forecast.revisions import (
    growth_revision_frame, revision_stats, revision_stats_by_phase,
    noise_vs_news, vintage_coverage,
)
pd.set_option("display.width", 120)
"""


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)


def nb1():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "name": "python3"}
    nb.cells = [
        md(
            "# Vintage matrices and the anatomy of revisions\n\n"
            "Every cell of a vintage matrix is a number as it was actually published "
            "on a given date. This notebook loads the four matrices used in the "
            "project (CPI and PPI monthly, PCE prices quarterly, from the Federal "
            "Reserve Bank of Philadelphia's Real-Time Data Set for Macroeconomists; "
            "retail sales monthly, rebuilt from ALFRED intervals for series RSAFS) "
            "and measures how first releases are later revised."
        ),
        code(SETUP),
        md("## Coverage, exactly as retrieved"),
        code(
            "matrices = {\n"
            "    'cpi': load_rtdsm_matrix('../data/raw/pcpiMvMd.xlsx', 'M'),\n"
            "    'ppi': load_rtdsm_matrix('../data/raw/pppiMvMd.xlsx', 'M'),\n"
            "    'retail': load_alfred_matrix('../data/raw/alfred_rsafs_vintages.csv', 'M'),\n"
            "    'pce': load_rtdsm_matrix('../data/raw/pconQvQd.xlsx', 'Q'),\n"
            "}\n"
            "pd.DataFrame({k: vintage_coverage(m) for k, m in matrices.items()}).T"
        ),
        md(
            "## Revision statistics on the growth scale\n\n"
            "Revisions are measured on growth rates (100 x log difference), "
            "maturity-restricted: an observation counts only if its first vintage "
            "is at least 24 vintages (monthly) or 8 vintages (quarterly) before "
            "the final vintage, so its latest value is close to settled."
        ),
        code(
            "frames = {\n"
            "    'cpi': growth_revision_frame(matrices['cpi'], 24),\n"
            "    'ppi': growth_revision_frame(matrices['ppi'], 24),\n"
            "    'retail': growth_revision_frame(matrices['retail'], 24),\n"
            "    'pce': growth_revision_frame(matrices['pce'], 8),\n"
            "}\n"
            "pd.DataFrame({k: revision_stats(f) for k, f in frames.items()}).T"
        ),
        md("## Revisions by business-cycle phase (NBER)"),
        code(
            "for key, frame in frames.items():\n"
            "    freq = 'Q' if key == 'pce' else 'M'\n"
            "    print(key)\n"
            "    print(pd.DataFrame(revision_stats_by_phase(frame, freq=freq)).T"
            "[['n', 'mean_revision', 'mean_abs_revision', 'reported']])"
        ),
        md(
            "## Noise or news?\n\n"
            "Regressing the revision on the first release: under a pure-news "
            "process the slope is zero. A nonzero slope means part of the first "
            "release was predictable error (noise) at release time."
        ),
        code(
            "pd.DataFrame({\n"
            "    'cpi': noise_vs_news(frames['cpi'], 12),\n"
            "    'ppi': noise_vs_news(frames['ppi'], 12),\n"
            "    'retail': noise_vs_news(frames['retail'], 12),\n"
            "    'pce': noise_vs_news(frames['pce'], 4),\n"
            "}).T"
        ),
        md(
            "## The revision-risk band\n\n"
            "The 90th percentile of the absolute revision of first-release growth "
            "is the band a decision-maker should attach to a release: nine times "
            "out of ten, the settled figure lands within this distance of the "
            "number first printed."
        ),
        code(
            "{k: round(float(f['revision_latest_minus_first'].abs().quantile(0.90)), 3)\n"
            " for k, f in frames.items()}"
        ),
    ]
    nbf.write(nb, NB / "01_vintage_matrices_and_revisions.ipynb")


def nb2():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "name": "python3"}
    nb.cells = [
        md(
            "# Honest versus naive: one benchmark, two information sets\n\n"
            "A fixed autoregressive benchmark (order by BIC inside each training "
            "window) is estimated at every forecast origin twice: on the vintage "
            "actually available then (honest) and on final data (naive). Both are "
            "scored against the same target, the latest-vintage growth of the "
            "target period. The gap is the flattery built into final-data "
            "evaluation."
        ),
        code(
            SETUP
            + "from realtime_forecast.forecast import run_evaluation, score, diebold_mariano, block_bootstrap_gap\n"
            + "from realtime_forecast.bridge import run_bridge_evaluation\n"
        ),
        md("## CPI (monthly origins, 2000-01 to 2025-12 vintages)"),
        code(
            "cpi = matrices_cpi = load_rtdsm_matrix('../data/raw/pcpiMvMd.xlsx', 'M')\n"
            "origins = [c for c in cpi.columns if pd.Period('2000-01', freq='M') <= c <= pd.Period('2025-12', freq='M')]\n"
            "fc_cpi = run_evaluation(cpi, origins, max_p=12, min_train=60)\n"
            "score(fc_cpi), diebold_mariano(fc_cpi), block_bootstrap_gap(fc_cpi, block=12)"
        ),
        md("## PPI (monthly origins, 2000-01 to 2025-12 vintages)"),
        code(
            "ppi = load_rtdsm_matrix('../data/raw/pppiMvMd.xlsx', 'M')\n"
            "origins_p = [c for c in ppi.columns if pd.Period('2000-01', freq='M') <= c <= pd.Period('2025-12', freq='M')]\n"
            "fc_ppi = run_evaluation(ppi, origins_p, max_p=12, min_train=60)\n"
            "score(fc_ppi), diebold_mariano(fc_ppi), block_bootstrap_gap(fc_ppi, block=12)"
        ),
        md(
            "## Retail sales (monthly origins; the window starts at the 2001-06 vintage)\n\n"
            "Retail sales comes from ALFRED (series RSAFS), whose vintage record "
            "begins with the 2001-06 vintage, so its usable origins run 2001-06 "
            "to 2025-12 rather than from 2000-01. The code below asks for the "
            "common 2000-01 to 2025-12 window; the origins that exist in the "
            "matrix are the ones that run."
        ),
        code(
            "retail = load_alfred_matrix('../data/raw/alfred_rsafs_vintages.csv', 'M')\n"
            "origins_r = [c for c in retail.columns if pd.Period('2000-01', freq='M') <= c <= pd.Period('2025-12', freq='M')]\n"
            "print('retail origins:', origins_r[0], '->', origins_r[-1], '=', len(origins_r))\n"
            "fc_retail = run_evaluation(retail, origins_r, max_p=12, min_train=60)\n"
            "score(fc_retail), diebold_mariano(fc_retail), block_bootstrap_gap(fc_retail, block=12)"
        ),
        md("## PCE prices, autoregressive arm (quarterly origins)"),
        code(
            "pce = load_rtdsm_matrix('../data/raw/pconQvQd.xlsx', 'Q')\n"
            "origins_q = [c for c in pce.columns if pd.Period('2000Q1', freq='Q') <= c <= pd.Period('2025Q4', freq='Q')]\n"
            "fc_pce = run_evaluation(pce, origins_q, max_p=4, min_train=40)\n"
            "score(fc_pce), diebold_mariano(fc_pce), block_bootstrap_gap(fc_pce, block=8)"
        ),
        md(
            "## PCE bridge specification\n\n"
            "The bridge forecasts the quarter's PCE inflation from the first "
            "month's CPI and PPI inflation (the only monthly data published by "
            "the middle month of the quarter, the aligned vintage) plus the "
            "previous quarter's PCE inflation. Same two arms."
        ),
        code(
            "bridge = run_bridge_evaluation(pce, cpi, ppi, origins_q, min_train=40)\n"
            "score(bridge), diebold_mariano(bridge), block_bootstrap_gap(bridge, block=8)"
        ),
        md(
            "## The leakage gate, demonstrated\n\n"
            "The engine asserts per origin that its training column equals the "
            "as-of vintage column. Corrupting every later vintage leaves the "
            "real-time forecasts of earlier origins unchanged; the test suite "
            "pins both properties."
        ),
        code(
            "from realtime_forecast.synthetic import make_synthetic_matrix\n"
            "syn, planted = make_synthetic_matrix()\n"
            "origins_s = list(syn.columns[90:96])\n"
            "clean = run_evaluation(syn, origins_s, max_p=4, min_train=60)\n"
            "corrupt = syn.copy()\n"
            "later = [c for c in corrupt.columns if c > origins_s[-1]]\n"
            "corrupt.loc[:, later] = (corrupt.loc[:, later] * 7.0).to_numpy()\n"
            "dirty = run_evaluation(corrupt, origins_s, max_p=4, min_train=60)\n"
            "(clean['realtime_forecast'].to_numpy() == dirty['realtime_forecast'].to_numpy()).all()"
        ),
    ]
    nbf.write(nb, NB / "02_honest_vs_naive.ipynb")


if __name__ == "__main__":
    NB.mkdir(exist_ok=True)
    nb1()
    nb2()
    print("notebooks built")
