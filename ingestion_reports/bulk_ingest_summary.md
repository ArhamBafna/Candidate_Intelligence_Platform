# Bulk Resume Ingestion Summary Report

- **Total Files Evaluated:** 76
- **Ingested (Valid Resumes):** 10
- **Skipped (Non-Resumes & Docs):** 66
- **Skipped (Duplicates):** 0
- **Failed / Ingestion Errors:** 0

---

## 1. Ingested Resumes

| # | Candidate Name | Parser Engine | AI Used | Folder | File Name |
|---|----------------|---------------|---------|--------|-----------|
| 1 | **Tisha Kanjilal** | `PyMuPDF_Parser` | No | `Candidate details` | `Tisha C 2024.pdf` |
| 2 | **Anand Prerna** | `PyMuPDF_Parser` | No | `Candidate details` | `Prerna_PO_USC_CA.pdf` |
| 3 | **Abhinay Govindaraju** | `Docx_Parser` | No | `Candidate details` | `Abhinay_dataengineer_H1B_VI.docx` |
| 4 | **Paid By Draft** | `PyMuPDF_Parser` | No | `Candidate details\Akshay` | `UtilityBill (1).pdf` |
| 5 | **Akshay Kumar Reddy Chamala** | `PyMuPDF_Parser` | Yes | `Candidate details\Akshay` | `082525 WellsFargo.pdf` |
| 6 | **Full Name Bhargavi Sanjaykumar** | `Docx_Parser` | No | `Candidate details\Bhargavi` | `Bhargavi submission details.docx` |
| 7 | **Uploaded Candidate** | `Docx_Parser` | No | `Candidate details\Eswar_Naveen_Java` | `Eswar Naveen java full stack.docx` |
| 8 | **Praveen Tippana** | `Docx_Parser` | No | `Candidate details\Praveen BIArch_CT_h1` | `PraveenTippana_Power BI Architect_H1B_CT.docx` |
| 9 | **Sai Kiran Pothula** | `Docx_Parser` | No | `Candidate details\Sai kiran` | `Sai_Kiran_Pothula_Full-Stack-Java-Developer (1).docx` |
| 10 | **Tamizharasan Senguttuvan** | `PyMuPDF_Parser` | No | `Candidate details\Tamiz` | `TAMIZHARASAN SENGUTTUVAN.pdf` |

---

## 2. Skipped Non-Resume Breakdown

| Category | Count | Common Reason / Document Type |
|----------|-------|-------------------------------|
| `SCANNED_IMAGE_REQUIRES_OCR` | **37** | Scanned document / image PDF without OCR text layer (<50 chars) |
| `STANDALONE_IMAGE` | **20** | Standalone image file (.jpg, .png, etc.) requiring OCR pipeline |
| `NON_RESUME_IMMIGRATION_OR_ID` | **4** | Government ID, Driver's License, Visa, Passport, or H-1B notice |
| `NON_RESUME_STUDY_OR_TEMPLATE` | **3** | Interview study guide, question bank, or submission template |
| `NON_RESUME_LEGAL_CONTRACT` | **1** | Legal contract, Referral Agreement, NDA, or Vendor Agreement |
| `AI_CLASSIFIED_NOT_RESUME` | **1** | No identifiable candidate name or contact information found |
