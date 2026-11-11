# Executive summary

**Question.** How much of a forecasting track record is real? When a model
is estimated and graded on final, revised data, part of its measured
accuracy was never available to anyone in real time. This project measures
that flattery for headline price indicators, and measures the revision
risk a decision-maker actually faces at release time.

**Data.** Full vintage matrices from the Federal Reserve Bank of
Philadelphia's Real-Time Data Set for Macroeconomists: CPI and PPI
(finished goods), 336 monthly vintages from
1998-11 to 2026-10; PCE
prices, 245 quarterly vintages from
1965Q4 to 2026Q4.
Retail sales, the fourth longlist indicator, has no keyless vintage
matrix (see the gate note); it is documented and scripted, not measured.

**Revisions.** On the growth scale, maturity-restricted: CPI mean revision
0.001 pp, mean absolute
0.031 pp, risk band plus or
minus 0.11 pp. PPI: mean
0.001 pp, mean absolute
0.080 pp, band plus or minus
0.28 pp. PCE (quarterly): mean
0.016 pp, mean absolute
0.133 pp, band plus or minus
0.30 pp. Revisions are partly predictable from the
first release (noise, not pure news): slopes
-0.030 (CPI,
p = 0.000769) and
-0.098 (PPI,
p = 1.65e-06); the PCE slope
(-0.039) is not
significant at 5% (p = 0.0519).
Revisions are larger in NBER contractions where the phase sample supports
reporting.

**The experiment.** One fixed autoregressive benchmark (order by BIC per
window), plus a bridge specification for PCE, estimated at every origin on
the as-of vintage and on final data, scored against the same
latest-vintage target. Final-data evaluation flatters every specification:
RMSE gaps (naive minus real-time) of
-0.005 pp (CPI,
310 origins, Diebold-Mariano
p = 0.0241),
-0.009 pp (PPI,
p = 0.407),
-0.012 pp (PCE
AR, p = 0.391), and
-0.036 pp (PCE bridge,
p = 0.399). Only the CPI gap is
statistically distinguishable from zero. Read plainly: for one-step price
benchmarks the flattery is small and mostly inside the noise, while the
revision risk in the target variable itself is an order of magnitude
larger. Both facts matter, and final-data evaluation hides the second one
entirely.

**Gate.** Synthetic planted-revision recovery and a per-origin leakage
assertion are enforced as automated tests; both pass. Nothing in the
project was tuned against these results: the benchmark, windows, and
maturity restrictions were fixed in the config before the run.
