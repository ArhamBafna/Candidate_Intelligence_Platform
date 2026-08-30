# Robust Candidate Name Extraction & False-Positive Prevention

The "blacklist" approach (adding words to `TITLE_IGNORE_HEADINGS`) is a game of whack-a-mole. You will endlessly discover new variations like *"Career Snapshot"*, *"Executive Bio"*, or *"My Journey"* that will break the parser.

Here are the most robust, generalized solutions to implement across NLP and extraction pipelines to avoid false-positive candidate names:

---

### 1. The Name-to-Email Similarity Check (Highest ROI)
Almost all professional resumes include an email address, and 95% of candidates use some variation of their name in their email prefix (e.g., `j.smith@`, `alexander.doe12@`).

**The Solution:** When the deterministic parser grabs a string like "Profile Summary" as the name, cross-reference it with the extracted email address prefix using a fuzzy string matching algorithm (like Jaro-Winkler).
* If the similarity is extremely low (e.g., "Profile Summary" vs "asmith"), immediately reject the deterministic name and force the AI to extract it. This is a very concrete, mathematically grounded safety net.

---

### 2. The Dictionary vs. Gazetteer Filter
A standard NLP technique is checking against dictionaries, but with a crucial caveat: many real names *are* dictionary words (e.g., "Rose", "Chase", "Hunter", "Joy", "Sterling").

**The Solution:** Use a double-filter. Load a standard English dictionary AND a "Gazetteer" (a large database of known global names, such as the US Census names database or NLTK's names corpus).
* If the extracted word is in the English dictionary but is **NOT** in the known-names database, reject it. This safely filters out "Profile", "Summary", and "Experience", while safely keeping "Hunter" and "Rose".

---

### 3. Positional Anchoring (Layout Heuristics)
Parsers that look at the first $N$ lines top-down fail when candidates put a header at the very top.

**The Solution:** Resumes are anchored by contact information. We already use highly accurate Regex to find the Email and Phone number. Instead of reading from the top-down, locate the **Contact Block**. The candidate's real name is almost universally 1 or 2 lines *directly above* or *on the same line* as the email/phone. By anchoring the search relative to the contact info, we bypass top-level section headers entirely.

---

### 4. Upgrade the NER (Named Entity Recognition) Engine
Small generic models like SpaCy's `en_core_web_sm` are trained on web blogs and news articles, expecting full sentences rather than isolated resume headers.

**The Solution:**
* Upgrade to a transformer-based model (e.g., `en_core_web_trf`) which handles formatting anomalies better.
* Implement **Negative Sampling**: Fine-tune the local model by feeding it resumes where section headers ("PROFILE SUMMARY") are explicitly labeled as *NOT* a person.

---

### Recommended Implementation Strategy
Combine **#1 (Name-to-Email Similarity)** and **#3 (Positional Anchoring)**. They do not require external ML models or massive dictionaries and rely on concrete anchors that already exist in every resume.
