# CSA1012 Software Engineering - Assignment 5 Demonstrator

Author: Muthu Krishnan K (Reg No 192511039)

Executable model for "Responsible Technology Adoption for the Examination and Credential Platform".
All data is synthetic. No real student data and no trained ML model is used.

## What it tests
- Keyword baseline (B0) vs revised rubric rules (R1) with paraphrase matching and a negation guard
- Moderation-priority queue vs a low-mark baseline
- Hash-chained audit log: tamper detection, truncation (with and without anchor), payload erasure
- Role and separation-of-duties checks, input validation, outbox for verifier outage
- Task 6: examiner-drift check, calibration to historical marks, weighted decision matrices and sensitivity

## Run
    python3 demo.py

Python 3.8+, standard library only. Seed is fixed (7), so results repeat exactly.
Output is printed and saved to `results.json`.

## Files
- `demo.py` - demonstrator
- `results.json` - output of the last run
- `diagrams/` - architecture, data-flow, workflow, and chart images used in the report
