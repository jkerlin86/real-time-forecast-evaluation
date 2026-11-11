# Coding decisions

1. **Data route.** The brief's first-choice vintage source was ALFRED.
   From the build environment, the keyless ALFRED graph-CSV endpoints
   return HTTP 403 to automated fetching, the FRED/ALFRED web hosts time
   out through the egress proxy, and the API host is key-gated. Rather
   than register a key with personal information (the owner's decision,
   per the project gate), the build uses the Philadelphia Fed's RTDSM,
   the standard research vintage archive, whose files cover CPI, PPI, and
   PCE prices completely. Retail sales has no RTDSM variable and no other
   keyless matrix; it is documented and scripted, not measured.

2. **Growth inside columns.** Growth rates are always computed within one
   vintage column. Computing a "first-release growth" from first-release
   levels of adjacent months would mix vintages and is never done.

3. **Maturity restriction.** Revision samples exclude observations whose
   first vintage is within 24 vintages (monthly) or 8 (quarterly) of the
   final vintage. The restriction materially changes the PCE numbers
   (benchmark revisions arrive late) and is applied identically to the
   synthetic gate, where the planted targets are known.

4. **Naive arm span.** The naive arm trains on the latest vintage
   restricted to the observation span the origin vintage contains. Letting
   it also use later observations would confound two different advantages
   (revised history versus longer history); the design isolates the
   revision effect only.

5. **Synthetic generator shape.** The generator's retained window starts
   mid-sample, as real RTDSM files do: observations published before the
   first retained vintage enter the matrix already carrying their planted
   noise at age counted from the window start, and the recovery test
   maturity-restricts, exactly as on real data. An earlier draft of the
   generator aged pre-window noise from the true publication date, which
   the as-built matrix cannot represent; the recovery test caught the
   factor-of-two error this produced, which is what the gate is for.

6. **Bridge alignment.** The quarterly PCE vintage for quarter q is
   aligned to the monthly vintage of q's middle month. At that date the
   first month of q is published in both monthly price series and the
   quarter's PCE index is not; the design uses exactly that information
   and no more.

7. **Uncertainty, both ways.** Every accuracy gap is reported with a
   Diebold-Mariano test and a block bootstrap, because the two disagree in
   emphasis on this sample (the CPI gap is significant by both; the PCE
   AR gap's bootstrap interval crosses zero while its point estimate is
   the second largest). Reporting only one would invite cherry-picking.

8. **The scripted ALFRED route was defective and was repaired
   (2026-11-10).** The follow-on run to add retail sales found the
   download script's ALFRED route could not produce a vintage matrix as
   written: it requested `series/observations` with `output=1` per
   vintage date, and that parameter returns only the current vintage's
   rows, whose realtime fields are `realtime_start` and `realtime_end`,
   not the `vintage_date` column the script tried to read (a KeyError on
   the first call). The route now uses the form that returns the full
   record: one request over the open realtime span (1776-07-04 to
   9999-12-31) with pagination, yielding one row per (observation,
   value-effective interval). For RSAFS that is 5,566 interval rows
   across 326 vintage dates, 2001-06-13 to 2026-10-15.

9. **ALFRED intervals become monthly snapshots, never pseudo-release
   dates.** ALFRED vintage dates are release dates, irregularly spaced.
   The project's pipeline, phase chronology, and snapshot timing
   conventions are monthly, and the RTDSM matrices it must stay
   comparable to are monthly snapshots. `load_alfred_matrix` therefore
   builds one column per month, each column holding the values whose
   effective interval covers the last ALFRED vintage date on or before
   that month's end. Retail inherits the monthly snapshot semantics (and
   their stated limitation: within-month release timing is not modelled)
   rather than a bespoke release-day timing no other indicator in the
   project uses. The alternative, analysing retail on its 326 release
   dates while the other indicators sit on monthly grids, was rejected:
   it would have made the cross-indicator comparison a comparison of two
   different timing conventions.

10. **Retail's window is stated, not silently narrowed.** The common
    monthly evaluation window is 2000-01 to 2025-12, but ALFRED's RSAFS
    vintage record begins 2001-06-13, so retail's first usable origin is
    the 2001-06 vintage (295 origins). The config keeps the common window
    for the series; the engine simply has no earlier columns to run, the
    results file records the actual origin window, and the README,
    executive summary, methods, and notebook 02 all state it. The other
    three indicators' numbers are untouched by the follow-on run
    (verified identical in the regenerated results file).
