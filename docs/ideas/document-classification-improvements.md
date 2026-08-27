# Multi-Signal Document Classification Improvements

## Problem
In bulk folder ingestion, non-resume documents such as utility bills (`UtilityBill (1).pdf`), bank account statements (`082525 WellsFargo.pdf`), and client candidate submission sheets (`Bhargavi submission details.docx`) bypassed the pre-intake classifier and were ingested as candidate profiles.

A naive single-word blacklist (e.g. rejecting any document with the word `"balance"` or `"account"`) risks rejecting valid accountant, financial analyst, or billing specialist resumes.

## Goal
Implement a robust multi-signal heuristic classifier in `classify_document()` that detects and rejects financial statements, utility bills, invoices, and payment receipts with zero false positives on genuine candidate resumes.

## Proposed Strategy

### 1. High-Confidence Filename Filtering
Evaluate filenames before reading content:
- Explicit financial & utility patterns: `*utility*bill*`, `*statement*of*account*`, `*bank*statement*`, `*paystub*`, `*w2*form*`, `*1099*`, `*tax*return*`.

### 2. Multi-Signal Body Clustering (Negative Clustered Heuristics)
Instead of matching single terms, require a **cluster score** ($\ge 3$ distinct financial signals) in the header/body:
- **Financial/Utility Cluster Tokens**:
  - `"amount due"`, `"past due amount"`, `"billing date"`, `"service address"`, `"paid by draft"`, `"account number"`, `"statement of accounts"`, `"previous balance"`, `"remit payment"`, `"total balance"`.
- **Resume Anchor Verification**:
  - Genuine resumes contain standard section anchors: `"experience"`, `"education"`, `"skills"`, `"projects"`, `"employment history"`, `"work history"`.
  - **Rule**: If a document has $\ge 2$ financial cluster tokens AND $0$ resume section anchors, classify as `NON_RESUME_FINANCIAL_OR_BILL` and reject immediately before parsing.

### 3. Submission Sheet Normalization
Detect internal vendor/recruiter candidate submission forms (e.g. `Bhargavi submission details.docx`):
- Detect key-value templates: `"Candidate Submission Details"`, `"Full Name\t"`, `"Rate\t"`, `"Visa Status\t"`.
- Strip table field prefixes (`"Full Name"`, `"Name:"`) so the actual candidate name is extracted cleanly rather than prepending `"Full Name"` to the candidate's first name.

## Benefits
- Prevents garbage profiles (like "Paid By Draft" with city hall phone numbers) from cluttering the talent pool.
- Protects financial/accounting candidates from being erroneously rejected.
- Zero extra latency (runs purely via regex string matching in microseconds).
