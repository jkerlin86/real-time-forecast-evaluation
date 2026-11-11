# Data

## What is here

`data/raw/` holds the vintage matrices exactly as downloaded (gitignored;
recreate with `scripts/download_data.py`). `data/processed/` holds the
derived artifacts written by `scripts/run_analysis.py`: one parquet vintage
matrix per measured indicator, the maturity-restricted revision frames, and
the per-origin forecast frames for the AR arms and the bridge.

## Sources

Three of the four measured indicators come from the **Real-Time Data Set
for Macroeconomists (RTDSM)**, maintained by the Federal Reserve Bank of
Philadelphia (Croushore and Stark):
https://www.philadelphiafed.org/surveys-and-data/real-time-data-research

The fourth, retail sales, comes from **ALFRED** (series RSAFS) via the
FRED API, retrieved 2026-11-10 under the free API key the project owner
registered at his own direction.

| File | Indicator | Originator | Bytes | SHA-256 | Coverage |
|---|---|---|---|---|---|
| pcpiMvMd.xlsx | CPI-U all items (PCPI) | U.S. Bureau of Labor Statistics | 829,636 | 2edd776f458f0c6d563e038ba364f0702d86b0b1da7e37fa3b097a0419076ece | 336 monthly vintages, 1998-11 to 2026-10; observations 1947-01 to 2026-09 |
| pppiMvMd.xlsx | PPI finished goods (PPPI) | U.S. Bureau of Labor Statistics | 813,286 | 8b7fd66c4b9e0f4686022fa83305762b736a18267c73fa8b609ba9b518283ae3 | 336 monthly vintages, 1998-11 to 2026-10; observations 1947-04 to 2026-09 |
| pconQvQd.xlsx | PCE price index (PCON) | U.S. Bureau of Economic Analysis | 250,558 | daac1f71863faaad8726c9940eac1f7c8de575b246fac1b30996e40c032a7d36 | 245 quarterly vintages, 1965Q4 to 2026Q4; observations 1947Q1 to 2026Q3 |
| alfred_rsafs_vintages.csv | Retail sales, advance retail trade and food services (RSAFS) | U.S. Census Bureau | 230,074 | 8f69adde6d80799bef129df91c8e2e93a59d91e7663082e36c6d6ee7c9d581cd | 5,566 value-effective interval rows; 326 ALFRED vintage dates, 2001-06-13 to 2026-10-15; observations 1992-01 to 2026-09 |

Retrieved 2026-11-10. The RTDSM is published for research use with
citation; the underlying observations are works of U.S. federal statistical
agencies, public domain at the originator.

## ALFRED reference series

| Indicator | ALFRED series | Source |
|---|---|---|
| CPI | CPIAUCSL | U.S. Bureau of Labor Statistics |
| PPI | PPIACO (all commodities, NSA; a different concept from the RTDSM finished-goods series used here) | U.S. Bureau of Labor Statistics |
| Retail sales | RSAFS | U.S. Census Bureau |
| PCE prices | PCEPI | U.S. Bureau of Economic Analysis |

FRED assigns each series one of three copyright statuses (Public Domain:
Citation requested; Copyrighted: Citation required; Copyrighted:
Pre-approval required). All four originators here are federal statistical
agencies whose data are public domain at the originator, and none of the
four series sits in the pre-approval tier. The FRED API terms page shown at
the owner's key registration carries no explicit caching or redistribution
wording; its Property Rights clause notes that some series are
third-party owned, which does not apply to the Census Bureau's RSAFS. The
measured values in this project are the RTDSM files above and the
ALFRED-retrieved RSAFS intervals; what the repository reports is the
derived statistics. `scripts/download_data.py --alfred` implements the
keyed ALFRED API route (key read from the `FRED_API_KEY` environment
variable or the project's `.env`; never commit a key).

## Retail sales: measured via ALFRED (follow-on, 2026-11-10)

Retail sales (RSAFS) was not measured in the original build: no keyless
vintage matrix for it exists (the RTDSM carries no retail variable, and
the Census Bureau's MARTS historic-release archive contains release
documents whose tables span a three-month window, not history snapshots;
chaining those windows would silently miss annual benchmark revisions).
After the owner registered the free FRED API key, the scripted ALFRED
route pulled the full interval record above. The loader
(`load_alfred_matrix`) rebuilds monthly snapshots from the intervals: one
column per month from 2001-06 to 2026-10 (305 snapshots), each the state
as of the last ALFRED vintage date on or before that month's end, the same
structure as the RTDSM matrices. Because ALFRED's RSAFS vintage record
begins 2001-06-13, retail's first usable evaluation origin is the 2001-06
vintage, not 2000-01; every retail output states that window.
