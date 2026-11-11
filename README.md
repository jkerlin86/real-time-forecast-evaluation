# The Revision Is the Story

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
  zero for CPI (0.001 pp) and PPI
  (0.001 pp), while mean absolute
  revisions are 0.031 pp (CPI),
  0.080 pp (PPI), and
  0.133 pp for quarterly PCE
  inflation. 51.9% of CPI growth
  observations and 60.5% of PPI
  observations are never revised at all; PCE observations always move.
- **Part of the first release is predictable error, not news.** Regressing
  the revision on the first release gives a slope of
  -0.098 for PPI
  (p = 1.65e-06) and
  -0.030 for CPI
  (p = 0.000769); a pure-news process
  would give zero. Revisions are also larger in contractions: mean absolute
  revisions of 0.251 pp
  (PPI) and 0.059 pp
  (CPI) against 0.074 pp
  and 0.030 pp in
  expansions.
- **The flattery is real but small for a one-step benchmark.** Scored
  against the same target (the latest vintage, treated as final), the
  final-data track record beats the honest one on every specification, by
  0.005 pp of
  RMSE for CPI, 0.009 pp
  for PPI, 0.012 pp for
  the PCE autoregression, and
  0.036 pp for the PCE
  bridge. For CPI the gap is statistically distinguishable from zero
  (Diebold-Mariano p = 0.0241;
  90% bootstrap interval
  [-0.010, -0.001]);
  for the other three it is not. Evaluating on final data overstates what a
  forecaster could have achieved, but for short-horizon price benchmarks the
  overstatement is a few thousandths of a percentage point of RMSE, far
  smaller than the revision risk in the target itself.
- **The honest uncertainty is at release time.** The revision-risk table
  below is the number a decision-maker should carry: the 90th percentile of
  the absolute revision of first-release growth. A first-release CPI growth
  print should be read as plus or minus 0.11 pp; a PPI
  print, plus or minus 0.28 pp; a quarterly PCE print,
  plus or minus 0.30 pp.

## Revision statistics (growth scale, maturity-restricted)

| Indicator | n | Mean revision | Mean abs. revision | Revised up | Revised down | Never revised | Risk band (p90 abs.) |
|---|---|---|---|---|---|---|---|
| CPI | 932 | 0.001 | 0.031 | 29.1% | 19.0% | 51.9% | 0.11 |
| PPI (finished goods) | 929 | 0.001 | 0.080 | 21.2% | 18.3% | 60.5% | 0.28 |
| PCE prices | 310 | 0.016 | 0.133 | 55.2% | 44.8% | 0.0% | 0.30 |

## Honest versus naive (RMSE in percentage points of growth)

Scoring target for both arms: latest-vintage growth of the target period
(the retrieved matrices end at the 2026-10 monthly
vintage and the 2026Q4 quarterly vintage). Latest is
treated as final, with the standing caveat that it is itself still revisable.

| Specification | Origins | Real-time RMSE | Final-data RMSE | Gap (naive minus real-time) | DM stat | DM p | Bootstrap 90% interval |
|---|---|---|---|---|---|---|---|
| CPI (AR) | 310 | 0.278 | 0.273 | -0.005 | -2.27 | 0.0241 | [-0.010, -0.001] |
| PPI (finished goods) (AR) | 312 | 0.778 | 0.769 | -0.009 | -0.83 | 0.407 | [-0.027, 0.012] |
| PCE prices (AR) | 104 | 0.424 | 0.413 | -0.012 | -0.86 | 0.391 | [-0.024, 0.004] |
| PCE prices (bridge) | 67 | 0.296 | 0.259 | -0.036 | -0.85 | 0.399 | [-0.093, 0.028] |

## Data and the licensing gate

The four longlist indicators are CPI, PPI, retail sales, and PCE prices.
Three are measured here from full vintage matrices published by the Federal
Reserve Bank of Philadelphia's Real-Time Data Set for Macroeconomists
(RTDSM): CPI (336 monthly vintages,
1998-11 to 2026-10), PPI
finished goods (336 monthly vintages), and PCE
prices (245 quarterly vintages,
1965Q4 to 2026Q4). The
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
planted revision noise (mean 0.06 pp,
mean absolute 0.165 pp) is run
through the same pipeline: it recovers a mean revision of
0.059 pp and a mean absolute revision of
0.166 pp. And the forecast engine asserts,
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
