APAAR SETU — SYNTHETIC DEMONSTRATION CSV PACK

All records are fictional. APAAR-like values are synthetic 12-digit format-test references and are NOT externally verified. All intake values are illustrative, not official AICTE approvals.

Files:
- programme_catalog.csv: curated institution/programme catalogue.
- apex_cse_baseline_2024_25.csv: 120 Apex CSE baseline records.
- apex_cse_candidate_2025_26.csv: 120 Apex CSE candidate records.
- national_polytechnic_roster_2024_25.csv: supporting source roster.
- kaveri_university_roster_2025_26.csv: supporting destination roster.
- transfer_event_support.csv: supporting transfer-event data; this may need manual creation if the roster importer does not create TransferEvent records.

Import order:
1. Confirm institutions and programmes exist.
2. Import Apex baseline before Apex candidate.
3. Import Polytechnic and Kaveri supporting rosters.
4. Create/confirm the three documented TransferEvent records.
5. Run reconciliation.

Expected Apex candidate: 115 continuing + 2 transfer-ins + 3 unexplained appearances = 120.
Expected Apex baseline: 115 continuing + 1 documented transfer-out + 4 withdrawals = 120.

Use the submission screen's header mapping. Do not assume every supplied column is supported by the current importer. Do not map any APAAR field to an external-verification status. These are demo-only records.
