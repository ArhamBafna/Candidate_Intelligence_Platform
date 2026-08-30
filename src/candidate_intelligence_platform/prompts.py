# Central home for every LLM prompt in the application.
#
# CATALOG (prompt | consumer | effect of edits):
# - Fact extraction          | ingestion AI fallback
#       (candidate_intelligence_platform/extraction/local_llm_fallback.extract_inferences)
#       | changes which facts the LLM extracts and the JSON schema it must return.
# - Candidate match insight  | GET /candidates/{candidate_id}/insight SSE stream
#       (api/routes/candidates.get_candidate_insight)
#       | changes the streamed match-rationale wording recruiters see.
# - Job-ad distillation      | job-ad parser AI paths
#       (candidate_intelligence_platform/search/job_ad_distiller._ai_distill_openrouter / _ai_distill_ollama)
#       | changes how job ads are parsed into title/skills/min_yoe/location.
#
# Rule: every LLM prompt lives here behind a named builder function — never inline
# at a call site (see AGENTS.md). Templates are private; builders are the public
# surface. Prompt text was moved here byte-identical; tests/test_prompts.py guards
# that with literal snapshots, so any rewording is a deliberate test-visible change.

from typing import Optional, Union

_EXTRACTION_TEMPLATE = """
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.

Rules:
- Output category strictly as one of: PERSON, CONTACT, EMPLOYMENT, SKILL, EDUCATION, LOCATION.
- claim_key must be the descriptor/type (e.g., 'name', 'email', 'phone', 'title', 'company', 'skill', 'degree', 'institution', 'location').
- claim_value must contain the actual extracted text snippet (NEVER null or empty).
- confidence_score must be a float between 0.80 and 1.00.
- NEVER extract job titles, adjectives, or introductory phrases (e.g. 'Experienced Software Engineer', 'Self-Motivated Professional') as a PERSON name. If no personal name is explicitly present, omit the PERSON claim.

Return ONLY valid JSON matching this schema:
{{
  "claims": [
    {{
      "claim_category": "PERSON",
      "claim_key": "name",
      "claim_value": "Jane Doe",
      "confidence_score": 0.95
    }},
    {{
      "claim_category": "CONTACT",
      "claim_key": "email",
      "claim_value": "jane@example.com",
      "confidence_score": 0.98
    }},
    {{
      "claim_category": "EMPLOYMENT",
      "claim_key": "title",
      "claim_value": "Senior Software Engineer",
      "confidence_score": 0.95
    }},
    {{
      "claim_category": "SKILL",
      "claim_key": "skill",
      "claim_value": "Python",
      "confidence_score": 0.92
    }},
    {{
      "claim_category": "EDUCATION",
      "claim_key": "degree",
      "claim_value": "B.S. in Computer Science",
      "confidence_score": 0.90
    }}
  ]
}}

Text:
{resume_text}
"""


def build_fact_extraction_prompt(resume_text: str) -> str:
    """Full fact-extraction prompt for the given (already truncated) resume text."""
    return _EXTRACTION_TEMPLATE.format(resume_text=resume_text)


def build_document_classification_prompt(text_sample: str) -> str:
    return (
        "You are a document classifier. Determine if the following text comes from a candidate resume/CV "
        "or a non-resume document (e.g. ID card, visa, passport, bill, contract).\n\n"
        f"Document text snippet:\n\"\"\"\n{text_sample[:1500]}\n\"\"\"\n\n"
        "Respond ONLY with a valid JSON object:\n"
        '{"is_resume": true|false, "category": "RESUME"|"ID"|"VISA"|"BILL"|"OTHER", "confidence": 0.0-1.0}'
    )


_INSIGHT_TEMPLATE = (
    "Given the candidate profile and resume text:\n"
    "{resume_text}\n\n"
    "Explain why this candidate is a good match for the search query: '{query}'. "
    "Provide a concise match rationale."
)

_INSIGHT_WITH_CRITERIA_TEMPLATE = (
    "Given the candidate profile and resume text:\n"
    "{resume_text}\n\n"
    "Explain why this candidate is a good match for the following search criteria:\n"
    "{criteria_block}\n\n"
    "Evaluate the candidate against all criteria above (job title, location/city, experience years, and required skills) and provide a concise match rationale."
)


def build_match_insight_prompt(
    resume_text: str,
    query: str,
    city: Optional[str] = None,
    job_title: Optional[str] = None,
    min_years: Optional[Union[float, int, str]] = None,
) -> str:
    """Match-rationale prompt for the given resume text, search query, and optional filters."""
    criteria_items = []
    if query and query.strip():
        criteria_items.append(f"- Search Query / Skills: '{query.strip()}'")
    if job_title and str(job_title).strip():
        criteria_items.append(f"- Target Job Title: {str(job_title).strip()}")
    if city and str(city).strip():
        criteria_items.append(f"- Target City / Location: {str(city).strip()}")
    if min_years is not None and str(min_years).strip():
        min_y_val = str(min_years).strip()
        if not min_y_val.endswith("years"):
            min_y_val = f"{min_y_val} years"
        criteria_items.append(f"- Minimum Experience: {min_y_val}")

    if not (city and str(city).strip()) and not (job_title and str(job_title).strip()) and not (min_years is not None and str(min_years).strip()):
        return _INSIGHT_TEMPLATE.format(resume_text=resume_text, query=query)

    criteria_block = "\n".join(criteria_items)
    return _INSIGHT_WITH_CRITERIA_TEMPLATE.format(
        resume_text=resume_text,
        criteria_block=criteria_block,
    )


_JOB_AD_DISTILL_TEMPLATE = """
You are a precise job-ad parser for a recruiting search engine.
Extract the structured requirements from the job advertisement below.

Return ONLY valid JSON with exactly these keys:
{{
  "title": "<job title or null>",
  "skills": ["must-have skill", "..."],
  "min_yoe": <number of required years of experience or null>,
  "location": "<job location or null>"
}}

Rules:
- Only include must-have requirements in "skills".
- "min_yoe" must be a plain number (e.g. 3 or 2.5) or null.
- Never invent values that are not stated in the ad.

Job advertisement:
{ad_text}
"""


def build_job_ad_distill_prompt(ad_text: str) -> str:
    """Job-ad parsing prompt for the given (already truncated) advertisement text."""
    return _JOB_AD_DISTILL_TEMPLATE.format(ad_text=ad_text)
