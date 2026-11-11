# Methods

## Design

Three questions, one dataset structure. A vintage matrix holds, for every
observation period (rows) and every vintage date (columns), the value as
published in that vintage. All analysis is on growth rates,
g = 100 x log(x_t / x_{t-1}), computed inside a single vintage column
(never across columns).

**Indicators.** CPI-U all items (RTDSM PCPI, BLS), PPI finished goods
(RTDSM PPPI, BLS), PCE chain-type price index (RTDSM PCON, BEA), and
retail sales (ALFRED RSAFS, U.S. Census Bureau). The PPI
concept is the finished-goods index, the headline PPI before the 2014
final-demand redesign and the concept the RTDSM archives; it is not
ALFRED's PPIACO (all commodities, not seasonally adjusted) and not the
final-demand index. PCE is quarterly because the RTDSM carries PCE prices
at quarterly vintages. Retail sales is sourced from ALFRED rather than the
RTDSM for a documented data reason (the RTDSM carries no retail variable;
see `data/README.md` and the project gate note): the scripted ALFRED route
pulls every value-effective interval for RSAFS, and the loader rebuilds
monthly snapshots from them, one column per month holding the state as of
the last ALFRED vintage date on or before that month's end. Retail then
runs through the identical pipeline with the identical settings as the
other monthly indicators. ALFRED's vintage record for RSAFS begins
2001-06-13, so the retail matrix has 305 monthly snapshots (2001-06 to
2026-10) against 336 for CPI and PPI, and its first usable evaluation
origin is the 2001-06 vintage.

## Revision analysis

For each observation, the first-release growth is the growth value in the
first vintage column in which it can be computed; the latest growth uses
the final column throughout. The revision is latest minus first. The
sample is maturity-restricted: an observation enters only if its first
vintage is at least 24 vintages before the final vintage (monthly) or 8
(quarterly). Without this restriction, recent observations, which have
barely begun to revise, mechanically understate revisions; the restriction
is the same one applied to the synthetic gate.

Reported: mean revision, mean and median absolute revision, standard
deviation, shares revised up, down, and never, the correlation of the
revision with the first release, and the 90th percentile of the absolute
revision, which the project publishes as the revision-risk band.

**Cycle phases.** NBER monthly chronology: peaks 2001-03, 2007-12,
2020-02; troughs 2001-11, 2009-06, 2020-04. A period is a contraction
observation if it falls in a peak-to-trough span; quarterly periods take
the phase of the quarter's middle month. Phase statistics are flagged
unreported below n = 24 (the PCE contraction cell, n = 11, is shown in the
results file with that flag and is not interpreted).

**Noise versus news.** OLS of the revision on the first release with
Newey-West (HAC) standard errors, lag 12 monthly and 4 quarterly. Under a
pure-news process the first release is an efficient estimate and the slope
is zero; a nonzero slope means a predictable component (noise) was present
at release. This is a diagnostic, not a structural estimate: the slope
also absorbs any correlation between true growth and the revision process.

## The honest-versus-naive experiment

**Specification (fixed, not tuned).** An autoregression on the growth
rate, order p chosen by BIC inside each training window over
p = 0..12 (monthly) or p = 0..4 (quarterly); p = 0 is the historical-mean
forecast. Estimated by least squares, recursively, at every origin.

**Origins and targets.** An origin is a vintage in the window
2000-01 to 2025-12 (monthly) or 2000Q1 to 2025Q4 (quarterly). Retail
sales is the one exception, stated wherever it is reported: ALFRED's
vintage record for RSAFS begins with the 2001-06 vintage, so its usable
origins are 2001-06 to 2025-12 (295 origins). At origin v,
the target period is the first observation not yet published in v
(one-step-ahead). Minimum training lengths: 60 growth observations
(monthly), 40 (quarterly).

**Arms.** The real-time arm trains on growth computed inside v's column.
The engine asserts, per origin, that the training column equals the as-of
column (`assert_no_future_vintage`); a leak raises rather than warns. The
naive arm trains the identical specification on the latest vintage over
the same observation span (observations up to the last one v contains).
Both arms are scored against the same number: the latest-vintage growth
of the target period. Scoring against latest is itself a convention;
latest is treated as final with the standing caveat that it remains
revisable (the matrices were retrieved 2026-11-10; later vintages will
move some targets slightly).

**Uncertainty.** Two statements accompany every gap: a Diebold-Mariano
test on the squared-error loss differential (Newey-West, lag 1, t
reference distribution), and a circular block bootstrap of the RMSE gap
(block 12 monthly, 8 quarterly; 2,000 replications; seed 20261110)
reporting the 90% percentile interval and the share of replications with a
negative gap.

## The bridge specification (PCE)

The bridge is the documented second specification, run for PCE only. The
origin is the quarterly vintage of quarter q (the file's vintage timing
places it after the quarter closes; the aligned monthly information is
the monthly vintage of q's middle month, by which only the first month of
q has been published). Regressors: the first month of q's CPI growth and
PPI growth (from the aligned monthly vintage in the real-time arm, from
the latest monthly vintage in the naive arm), the previous quarter's PCE
growth (vintage-consistent), and a constant. The equation is estimated on
all quarters before q with at least 40 training quarters, and forecasts
quarter q's PCE growth. Scoring and uncertainty are identical to the AR
experiment. Usable origins: 67 of the 104 quarterly origins in the window,
the rest failing the training-length or first-month-availability
requirements; the count is reported, not hidden.

## The validation gate

A synthetic matrix is generated with a known AR(1) growth process and
planted first-release noise (mean -0.06 pp, sd 0.20 pp) that each vintage
removes geometrically (share 0.5). Known targets: mean revision +0.06,
mean absolute revision = mean absolute planted noise. The pipeline must
recover both within 0.02 pp (it recovers them to within 0.001 pp), and the
leakage properties must hold functionally: corrupting all vintages after
a set of origins leaves those origins' real-time forecasts bit-identical,
and a training column taken from a later vintage trips the assertion.
Both are automated tests in `tests/`. A failed gate fails the build.

## Limitations

1. The scoring target (latest vintage) is a moving target treated as
   fixed; results are conditional on the 2026-10 / 2026Q4 final columns.
2. One-step horizons only. The flattery of final-data evaluation grows
   with horizon in most applications; nothing here bounds it at longer
   horizons.
3. The benchmark is deliberately plain. A forecaster who modelled the
   revision process itself (the noise diagnostic says some of it is
   predictable) could close part of the honest gap; that is a modelling
   project, not an evaluation project, and is out of scope by design.
4. RTDSM vintages are monthly (prices) snapshots of the release process,
   not the release-day record; within-month release timing is not
   modelled. The bridge's middle-month alignment is the one place timing
   is approximated, and it is stated where used.
5. PCE revisions include benchmark and comprehensive revisions of the
   national accounts, which are larger and less frequent than monthly
   price revisions; the quarterly maturity restriction (8 vintages, two
   years) is shorter relative to that process than the monthly one.
6. The retail matrix is a monthly-snapshot reconstruction of ALFRED's
   release-date record: a month holding more than one RSAFS vintage date
   contributes only its last state as a column. RSAFS has 326 vintage
   dates across 305 snapshot months, so the coarsening is small, but the
   within-month revision detail is not in the matrix.
7. Retail's evaluation window starts in 2001-06, not 2000-01, because
   that is where ALFRED's RSAFS vintage record starts; cross-indicator
   comparisons involving retail cover a slightly shorter, later window
   than the CPI and PPI comparisons.
