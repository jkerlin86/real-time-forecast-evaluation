# Data

## What is here

`data/raw/` holds the vintage matrices exactly as downloaded (gitignored;
recreate with `scripts/download_data.py`). `data/processed/` holds the
derived artifacts written by `scripts/run_analysis.py`: one parquet vintage
matrix per measured indicator, the maturity-restricted revision frames, and
the per-origin forecast frames for the AR arms and the bridge.

## Sources

All measured values come from the **Real-Time Data Set for Macroeconomists
(RTDSM)**, maintained by the Federal Reserve Bank of Philadelphia
(Croushore and Stark):
https://www.philadelphiafed.org/surveys-and-data/real-time-data-research

| File | Indicator | Originator | Bytes | SHA-256 | Coverage |
|---|---|---|---|---|---|
| pcpiMvMd.xlsx | CPI-U all items (PCPI) | U.S. Bureau of Labor Statistics | 829,636 | 2edd776f458f0c6d563e038ba364f0702d86b0b1da7e37fa3b097a0419076ece | 336 monthly vintages, 1998-11 to 2026-10; observations 1947-01 to 2026-09 |
| pppiMvMd.xlsx | PPI finished goods (PPPI) | U.S. Bureau of Labor Statistics | 813,286 | 8b7fd66c4b9e0f4686022fa83305762b736a18267c73fa8b609ba9b518283ae3 | 336 monthly vintages, 1998-11 to 2026-10; observations 1947-04 to 2026-09 |
| pconQvQd.xlsx | PCE price index (PCON) | U.S. Bureau of Economic Analysis | 250,558 | daac1f71863faaad8726c9940eac1f7c8de575b246fac1b30996e40c032a7d36 | 245 quarterly vintages, 1965Q4 to 2026Q4; observations 1947Q1 to 2026Q3 |

Retrieved 2026-11-10. The RTDSM is published for research use with
citation; the underlying observations are works of U.S. federal statistical
agencies, public domain at the originator.

## ALFRED reference series (not redistributed)

| Indicator | ALFRED series | Source |
|---|---|---|
| CPI | CPIAUCSL | U.S. Bureau of Labor Statistics |
| PPI | PPIACO (all commodities, NSA; a different concept from the RTDSM finished-goods series used here) | U.S. Bureau of Labor Statistics |
| Retail sales | RSAFS | U.S. Census Bureau |
| PCE prices | PCEPI | U.S. Bureau of Economic Analysis |

FRED assigns each series one of three copyright statuses (Public Domain:
Citation requested; Copyrighted: Citation required; Copyrighted:
Pre-approval required). All four originators here are federal statistical
agencies whose data are public at the originator. FRED's Services Terms of
Use additionally prohibit caching or archiving FRED content for
third-party provision and any use in developing or training machine
learning systems. This project therefore redistributes **no FRED or ALFRED
values**: the measured values are the RTDSM files above plus derived
statistics. `scripts/download_data.py --alfred` implements the keyed ALFRED
API route for a reader's own analysis (key read from the `FRED_API_KEY`
environment variable; never commit a key).

## The retail sales gap

Retail sales (RSAFS) is the fourth longlist indicator and is **not
measured** in this build. No keyless vintage matrix for it exists: the
RTDSM carries no retail variable, and the Census Bureau's MARTS
historic-release archive contains release documents whose tables span a
three-month window, not history snapshots (verified by direct inspection
of rs1704.xls, the April 2017 release file). Chaining three-month windows
would silently miss annual benchmark revisions of older observations. The
ALFRED API route in the download script builds the retail matrix when a
reader supplies a free FRED API key; the analysis pipeline accepts it
without code changes (register the series in `configs/default.json`).
