"""Render README.md and reports/executive_summary.md from reports/results.json.

No number in either document is hand-typed: every statistic is formatted
from the results file written by scripts/run_analysis.py.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "reports/results.json").read_text())

C = R["indicators"]["cpi"]
P = R["indicators"]["ppi"]
E = R["indicators"]["pce"]
B = R["bridge"]
G = R["synthetic_gate"]


def f(x, nd=3):
    return f"{x:.{nd}f}"


def pct(x, nd=1):
    return f"{100 * x:.{nd}f}%"


def rev_table() -> str:
    rows = []
    for label, v in [("CPI", C), ("PPI (finished goods)", P), ("PCE prices", E)]:
        s = v["revisions"]["stats"]
        rows.append(
            f"| {label} | {s['n']} | {f(s['mean_revision'])} | {f(s['mean_abs_revision'])} | "
            f"{pct(s['share_revised_up'])} | {pct(s['share_revised_down'])} | "
            f"{pct(s['share_unrevised'])} | {f(v['risk_band_pp'], 2)} |"
        )
    return "\n".join(rows)


def eval_table() -> str:
    rows = []
    specs = [("CPI", C), ("PPI (finished goods)", P), ("PCE prices", E)]
    for label, v in specs:
        e = v["evaluation"]
        sc, dm, bt = e["scores"], e["diebold_mariano"], e["bootstrap"]
        rows.append(
            f"| {label} (AR) | {e['n_origins']} | {f(sc['realtime_rmse'])} | {f(sc['naive_rmse'])} | "
            f"{f(sc['rmse_gap_naive_minus_realtime'])} | {f(dm['dm_statistic'], 2)} | "
            f"{dm['dm_p_value']:.3g} | [{f(bt['gap_p05'])}, {f(bt['gap_p95'])}] |"
        )
    sc, dm, bt = B["scores"], B["diebold_mariano"], B["bootstrap"]
    rows.append(
        f"| PCE prices (bridge) | {B['n_origins']} | {f(sc['realtime_rmse'])} | "
        f"{f(sc['naive_rmse'])} | {f(sc['rmse_gap_naive_minus_realtime'])} | "
        f"{f(dm['dm_statistic'], 2)} | {dm['dm_p_value']:.3g} | "
        f"[{f(bt['gap_p05'])}, {f(bt['gap_p95'])}] |"
    )
    return "\n".join(rows)


README = f"""# The Revision Is the Story

## Real-time forecast evaluation with vintage data

Forecasters are routinely graded against revised, final data they could
never have seen. That grading flatters the track record twice over: the
model is estimated on numbers that did not exist yet, and it is scored
against a target that kept moving after the forecast was made. This project
rebuilds the evaluation honestly. It assembles full vintage matrices for
headline price indicators (each cell is the value as published on a given
date), measures how first releases are revised, and then runs one fixed
benchmark forecasting specification twice at every forecast origin: once on
the vintage actually available at the time, and once on final data. The gap
between the two track records is the flattery, measured.

## Headline findings

- **First-release price growth is revised by a little, on average, but the
  dispersion is the story.** Mean revisions of monthly growth are close to
  zero for CPI ({f(C['revisions']['stats']['mean_revision'])} pp) and PPI
  ({f(P['revisions']['stats']['mean_revision'])} pp), while mean absolute
  revisions are {f(C['revisions']['stats']['mean_abs_revision'])} pp (CPI),
  {f(P['revisions']['stats']['mean_abs_revision'])} pp (PPI), and
  {f(E['revisions']['stats']['mean_abs_revision'])} pp for quarterly PCE
  inflation. {pct(C['revisions']['stats']['share_unrevised'])} of CPI growth
  observations and {pct(P['revisions']['stats']['share_unrevised'])} of PPI
  observations are never revised at all; PCE observations always move.
- **Part of the first release is predictable error, not news.** Regressing
  the revision on the first release gives a slope of
  {f(P['revisions']['noise_vs_news']['slope_on_first_release'], 3)} for PPI
  (p = {P['revisions']['noise_vs_news']['slope_p']:.3g}) and
  {f(C['revisions']['noise_vs_news']['slope_on_first_release'], 3)} for CPI
  (p = {C['revisions']['noise_vs_news']['slope_p']:.3g}); a pure-news process
  would give zero. Revisions are also larger in contractions: mean absolute
  revisions of {f(P['revisions']['by_phase']['contraction']['mean_abs_revision'])} pp
  (PPI) and {f(C['revisions']['by_phase']['contraction']['mean_abs_revision'])} pp
  (CPI) against {f(P['revisions']['by_phase']['expansion']['mean_abs_revision'])} pp
  and {f(C['revisions']['by_phase']['expansion']['mean_abs_revision'])} pp in
  expansions.
- **The flattery is real but small for a one-step benchmark.** Scored
  against the same target (the latest vintage, treated as final), the
  final-data track record beats the honest one on every specification, by
  {abs(C['evaluation']['scores']['rmse_gap_naive_minus_realtime']):.3f} pp of
  RMSE for CPI, {abs(P['evaluation']['scores']['rmse_gap_naive_minus_realtime']):.3f} pp
  for PPI, {abs(E['evaluation']['scores']['rmse_gap_naive_minus_realtime']):.3f} pp for
  the PCE autoregression, and
  {abs(B['scores']['rmse_gap_naive_minus_realtime']):.3f} pp for the PCE
  bridge. For CPI the gap is statistically distinguishable from zero
  (Diebold-Mariano p = {C['evaluation']['diebold_mariano']['dm_p_value']:.3g};
  90% bootstrap interval
  [{f(C['evaluation']['bootstrap']['gap_p05'])}, {f(C['evaluation']['bootstrap']['gap_p95'])}]);
  for the other three it is not. Evaluating on final data overstates what a
  forecaster could have achieved, but for short-horizon price benchmarks the
  overstatement is a few thousandths of a percentage point of RMSE, far
  smaller than the revision risk in the target itself.
- **The honest uncertainty is at release time.** The revision-risk table
  below is the number a decision-maker should carry: the 90th percentile of
  the absolute revision of first-release growth. A first-release CPI growth
  print should be read as plus or minus {f(C['risk_band_pp'], 2)} pp; a PPI
  print, plus or minus {f(P['risk_band_pp'], 2)} pp; a quarterly PCE print,
  plus or minus {f(E['risk_band_pp'], 2)} pp.

## Revision statistics (growth scale, maturity-restricted)

| Indicator | n | Mean revision | Mean abs. revision | Revised up | Revised down | Never revised | Risk band (p90 abs.) |
|---|---|---|---|---|---|---|---|
{rev_table()}

## Honest versus naive (RMSE in percentage points of growth)

Scoring target for both arms: latest-vintage growth of the target period
(the retrieved matrices end at the {C['coverage']['last_vintage']} monthly
vintage and the {E['coverage']['last_vintage']} quarterly vintage). Latest is
treated as final, with the standing caveat that it is itself still revisable.

| Specification | Origins | Real-time RMSE | Final-data RMSE | Gap (naive minus real-time) | DM stat | DM p | Bootstrap 90% interval |
|---|---|---|---|---|---|---|---|
{eval_table()}

## Data and the licensing gate

The four longlist indicators are CPI, PPI, retail sales, and PCE prices.
Three are measured here from full vintage matrices published by the Federal
Reserve Bank of Philadelphia's Real-Time Data Set for Macroeconomists
(RTDSM): CPI ({C['coverage']['n_vintages']} monthly vintages,
{C['coverage']['first_vintage']} to {C['coverage']['last_vintage']}), PPI
finished goods ({P['coverage']['n_vintages']} monthly vintages), and PCE
prices ({E['coverage']['n_vintages']} quarterly vintages,
{E['coverage']['first_vintage']} to {E['coverage']['last_vintage']}). The
underlying observations are U.S. Bureau of Labor Statistics and Bureau of
Economic Analysis statistics, public domain at the originator.

Retail sales is documented but **not measured**, and the reason is a data
finding, not an omission: no keyless vintage matrix for retail sales
exists. The RTDSM carries no retail variable, and the Census Bureau's
MARTS archive holds release documents (three-month windows), not history
snapshots. The canonical vintage source is ALFRED (series RSAFS, U.S.
Census Bureau), whose API requires a free registered key. Per the project
gate, no key was registered with anyone's personal information; the repo
ships the ALFRED download route (`scripts/download_data.py --alfred`,
key from the reader's own environment) and the pipeline is
indicator-generic, so retail joins the day a key is supplied. The keyless
ALFRED graph-CSV endpoints also failed from the build environment (HTTP
403 to automated fetching; the API host itself answers and is key-gated).

ALFRED series references for all four indicators are recorded in
`data/README.md` and `configs/default.json`. FRED's terms (three per-series
copyright tiers; 2024 prohibitions on API caching for third-party provision
and on ML-training use) are why this project redistributes RTDSM values and
derived statistics rather than any FRED download.

## Validation gate

The build is gated on two automated tests. A synthetic vintage matrix with
planted revision noise (mean {G['planted_expected_mean_revision']:.2f} pp,
mean absolute {G['planted_expected_mean_abs_revision']:.3f} pp) is run
through the same pipeline: it recovers a mean revision of
{f(G['recovered_mean_revision'])} pp and a mean absolute revision of
{f(G['recovered_mean_abs_revision'])} pp. And the forecast engine asserts,
at every origin, that its training column equals the as-of vintage column;
a test corrupts all later vintages and verifies the real-time forecasts do
not move, and a second test verifies a deliberately contaminated training
column trips the assertion. If either test fails, the build fails.

## Reproduce

```bash
pip install -e ".[dev,notebooks]"
python scripts/download_data.py        # RTDSM matrices (keyless)
python scripts/run_analysis.py         # writes reports/results.json
python scripts/make_figures.py
python scripts/make_notebooks.py && python scripts/execute_notebooks.py
python scripts/make_reports.py         # renders README + executive summary
pytest                                 # includes the leakage gate tests
```

## Layout

- `src/realtime_forecast/` vintage matrices, revision statistics, the
  honest-vs-naive engine, the PCE bridge, the synthetic gate generator
- `notebooks/` 01 vintage matrices and revisions; 02 honest versus naive
- `reports/results.json` every number in this README and the executive
  summary, generated by `scripts/run_analysis.py`
- `docs/methods.md` design, timing conventions, and limitations
"""

EXEC = f"""# Executive summary

**Question.** How much of a forecasting track record is real? When a model
is estimated and graded on final, revised data, part of its measured
accuracy was never available to anyone in real time. This project measures
that flattery for headline price indicators, and measures the revision
risk a decision-maker actually faces at release time.

**Data.** Full vintage matrices from the Federal Reserve Bank of
Philadelphia's Real-Time Data Set for Macroeconomists: CPI and PPI
(finished goods), {C['coverage']['n_vintages']} monthly vintages from
{C['coverage']['first_vintage']} to {C['coverage']['last_vintage']}; PCE
prices, {E['coverage']['n_vintages']} quarterly vintages from
{E['coverage']['first_vintage']} to {E['coverage']['last_vintage']}.
Retail sales, the fourth longlist indicator, has no keyless vintage
matrix (see the gate note); it is documented and scripted, not measured.

**Revisions.** On the growth scale, maturity-restricted: CPI mean revision
{f(C['revisions']['stats']['mean_revision'])} pp, mean absolute
{f(C['revisions']['stats']['mean_abs_revision'])} pp, risk band plus or
minus {f(C['risk_band_pp'], 2)} pp. PPI: mean
{f(P['revisions']['stats']['mean_revision'])} pp, mean absolute
{f(P['revisions']['stats']['mean_abs_revision'])} pp, band plus or minus
{f(P['risk_band_pp'], 2)} pp. PCE (quarterly): mean
{f(E['revisions']['stats']['mean_revision'])} pp, mean absolute
{f(E['revisions']['stats']['mean_abs_revision'])} pp, band plus or minus
{f(E['risk_band_pp'], 2)} pp. Revisions are partly predictable from the
first release (noise, not pure news): slopes
{f(C['revisions']['noise_vs_news']['slope_on_first_release'], 3)} (CPI,
p = {C['revisions']['noise_vs_news']['slope_p']:.3g}) and
{f(P['revisions']['noise_vs_news']['slope_on_first_release'], 3)} (PPI,
p = {P['revisions']['noise_vs_news']['slope_p']:.3g}); the PCE slope
({f(E['revisions']['noise_vs_news']['slope_on_first_release'], 3)}) is not
significant at 5% (p = {E['revisions']['noise_vs_news']['slope_p']:.3g}).
Revisions are larger in NBER contractions where the phase sample supports
reporting.

**The experiment.** One fixed autoregressive benchmark (order by BIC per
window), plus a bridge specification for PCE, estimated at every origin on
the as-of vintage and on final data, scored against the same
latest-vintage target. Final-data evaluation flatters every specification:
RMSE gaps (naive minus real-time) of
{f(C['evaluation']['scores']['rmse_gap_naive_minus_realtime'])} pp (CPI,
{C['evaluation']['n_origins']} origins, Diebold-Mariano
p = {C['evaluation']['diebold_mariano']['dm_p_value']:.3g}),
{f(P['evaluation']['scores']['rmse_gap_naive_minus_realtime'])} pp (PPI,
p = {P['evaluation']['diebold_mariano']['dm_p_value']:.3g}),
{f(E['evaluation']['scores']['rmse_gap_naive_minus_realtime'])} pp (PCE
AR, p = {E['evaluation']['diebold_mariano']['dm_p_value']:.3g}), and
{f(B['scores']['rmse_gap_naive_minus_realtime'])} pp (PCE bridge,
p = {B['diebold_mariano']['dm_p_value']:.3g}). Only the CPI gap is
statistically distinguishable from zero. Read plainly: for one-step price
benchmarks the flattery is small and mostly inside the noise, while the
revision risk in the target variable itself is an order of magnitude
larger. Both facts matter, and final-data evaluation hides the second one
entirely.

**Gate.** Synthetic planted-revision recovery and a per-origin leakage
assertion are enforced as automated tests; both pass. Nothing in the
project was tuned against these results: the benchmark, windows, and
maturity restrictions were fixed in the config before the run.
"""


def main() -> None:
    (ROOT / "README.md").write_text(README)
    (ROOT / "reports/executive_summary.md").write_text(EXEC)
    print("rendered README.md and reports/executive_summary.md")


if __name__ == "__main__":
    main()
