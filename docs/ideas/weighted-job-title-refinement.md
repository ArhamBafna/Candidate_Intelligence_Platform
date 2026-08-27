# Weighted Job Title Extraction & Refinement

## Problem
During deterministic extraction, keywords like `"lead"`, `"engineer"`, or `"architect"` matched inside sentences or educational degrees:
- Sentence: `"Able lead development team..."` $\rightarrow$ extracted job title: `"Able lead"`.
- Education table: `"Bachelors in Computer Science and Engineer"` $\rightarrow$ extracted job title: `"Bachelors in Computer Science and Engineer"`.
- Summary statement: `"Proven Backend Engineer with 7 years experience..."` $\rightarrow$ extracted job title: `"Proven Backend Engineer"`.

## Goal
Implement a scoring and weight-based title extractor that accurately scores candidate job titles across different resume sections, strips extraneous adjectives/verbs, and prefers top-of-page header titles over low-confidence mentions.

## Proposed Strategy

### 1. Section-Weighted Confidence Scoring
Rather than completely excluding sections where titles might legitimately appear (e.g., in projects or certifications), assign location-based weights:
- **Header / Sub-header (Lines 1–10, under candidate name)**: **Weight = 1.0** (Highest confidence).
- **Professional Summary / Objective**: **Weight = 0.70**.
- **Experience / Work History Section Headings**: **Weight = 0.85**.
- **Projects Section**: **Weight = 0.35** (Low score).
- **Education & Certifications Section**: **Weight = 0.15** (Very low score; used only as fallback if no other title exists).

### 2. Syntactic Role Matcher & Prefix Stripping
Apply regex pattern matching to clean title phrases:
- **Noise / Prefix Stripper**:
  - Remove leading verbs/adjectives: `^(?:Proven|Experienced|Dynamic|Dedicated|Passionate|Seasoned|Able|Skilled|Senior-level|Junior-level)\s+`
  - Example: `"Proven Backend Engineer with 7 years..."` $\rightarrow$ cleanly extracts `"Backend Engineer"`.
- **Role Grammar Anchor**:
  - Match structured job titles:
    `^(?:Senior |Lead |Staff |Principal |Associate |Junior |Chief )?(?:Full Stack |Front[- ]?End |Back[- ]?End |Cloud |DevOps |Data |AI/ML |BI |QA |Systems )?(?:Software |Data |Security |Platform )?(?:Engineer|Developer|Architect|Analyst|Consultant|Manager|Director|Specialist|Administrator)$`
- **Verb Filter**:
  - Discard matches where the title keyword is used as a verb (e.g., `"Able lead..."`, `"Helped develop..."`, `"Manage team of..."`).

### 3. Selection Algorithm
1. Extract candidate title candidates across all lines.
2. Calculate score: $\text{Final Score} = \text{Section Weight} \times \text{Syntactic Pattern Match Score} - \text{Length Penalty}$.
3. Select the highest-scoring candidate title exceeding the threshold (e.g. $\ge 0.50$).
4. If highest score is below threshold, trigger AI LLM fallback.

## Benefits
- Retains valid titles mentioned in non-standard sections while heavily penalizing noise like degree names.
- Eliminates awkward title strings like `"Able lead"` or `"Proven Backend Engineer"`.
- Provides deterministic, explainable scoring.
