# RootScore — Codex Prompt Log
**Project:** RootScore — Neighborhood Eviction Risk Tool  
**Contest:** OpenAI Codex Contest 2026  
**Author:** Tim Slimak  
**Submission Deadline:** April 30, 2026

---

## Prompt 001 — Workspace Inspection and Project Initialization
**Date:** 2026-03-26  
**Purpose:** Determine whether the Codex sandbox contains existing project files, configuration files, or Python patterns to follow before generating new scripts.

**Prompt:**  
I'm going to inspect the workspace for census_config.json and see whether there's an existing Python project or script pattern to follow, then I'll add the ACS pull script and verify the output shape.

**Codex Output Summary:**  
Codex inspected the workspace using PowerShell commands, confirmed the repository was empty, and determined that no existing Python project structure or configuration files were present. It concluded that a self-contained ingestion script would be required and prepared the environment for generating new project files.

**Key Design Decisions:**  
- Self-contained script architecture chosen since no existing project patterns were present  
- census_config.json established as the API key storage pattern for all future ingestion scripts  
- Codex confirmed environment readiness before any code generation began

**Next:** Prompt 002 — ACS Tract-Level Ingestion Script

---

## Prompt 002 — ACS Tract-Level Ingestion Script
**Date:** 2026-03-26  
**Purpose:** Generate a complete ACS ingestion pipeline with county-level batching.

**Prompt:**  
Write a Python script that pulls census tract-level data from the Census ACS 5-Year API (2022) for all tracts in the United States. Fields to retrieve: median household income (B19013_001E), gross rent as a percentage of household income (B25070_010E for 35%+ burden), total renter-occupied units (B25003_003E), total housing units (B25001_001E), unemployment rate proxy (B23025_005E for unemployed, B23025_003E for labor force), and median gross rent (B25064_001E). Use the census_config.json file for the API key. Output a clean pandas DataFrame saved to acs_tract_data.csv with a standardized 11-digit GEOID column.

**Codex Output Summary:**  
Codex generated pull_acs_tract_data.py, including config loading, county-level batching, tract-level ACS pulls, GEOID standardization, derived metrics, and CSV output. The script compiled successfully.

**Key Design Decisions:**  
- County-level batching chosen over state-level to avoid Census API timeouts  
- Exponential backoff with 5 retries added for retry resilience on dropped connections  
- GEOID zero-padded to 11 digits as the universal merge key for all five data sources  
- Two derived features computed at ingestion time: rent_burden_35_plus_share and unemployment_rate_proxy  
- Sentinel values coerced to NaN via pd.to_numeric(errors="coerce") to handle Census API -999999999 patterns

**Next:** Prompt 003 — Eviction Lab Ingestion Script

---

## Prompt 003 — Eviction Lab Ingestion Script
*(Coming next)*

---
