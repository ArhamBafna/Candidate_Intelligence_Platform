"""Guard tests: prompts moved into candidate_intelligence_platform.prompts must stay
byte-identical to the text that previously lived inline at the call sites.

These snapshots pin the exact bytes sent to the LLM. Rewording a prompt is a
deliberate behavior change and must update the snapshot here on purpose.
"""
from candidate_intelligence_platform.prompts import (
    build_fact_extraction_prompt,
    build_job_ad_distill_prompt,
    build_match_insight_prompt,
    build_consolidated_match_insight_prompt,
    build_batched_extraction_prompt,
    build_json_repair_prompt,
)


def test_fact_extraction_prompt_is_byte_identical() -> None:
    rendered = build_fact_extraction_prompt("Jane Doe\nSenior Engineer")
    expected = """
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.

Rules:
- Output category strictly as one of: PERSON, CONTACT, EMPLOYMENT, SKILL, EDUCATION, LOCATION.
- claim_key must be the descriptor/type (e.g., 'name', 'email', 'phone', 'title', 'company', 'skill', 'degree', 'institution', 'location').
- claim_value must contain the actual extracted text snippet (NEVER null or empty).
- confidence_score must be a float between 0.80 and 1.00.
- NEVER extract job titles, adjectives, or introductory phrases (e.g. 'Experienced Software Engineer', 'Self-Motivated Professional') as a PERSON name. If no personal name is explicitly present, omit the PERSON claim.

Return ONLY valid JSON matching this schema:
{
  "claims": [
    {
      "claim_category": "PERSON",
      "claim_key": "name",
      "claim_value": "Jane Doe",
      "confidence_score": 0.95
    },
    {
      "claim_category": "CONTACT",
      "claim_key": "email",
      "claim_value": "jane@example.com",
      "confidence_score": 0.98
    },
    {
      "claim_category": "EMPLOYMENT",
      "claim_key": "title",
      "claim_value": "Senior Software Engineer",
      "confidence_score": 0.95
    },
    {
      "claim_category": "SKILL",
      "claim_key": "skill",
      "claim_value": "Python",
      "confidence_score": 0.92
    },
    {
      "claim_category": "EDUCATION",
      "claim_key": "degree",
      "claim_value": "B.S. in Computer Science",
      "confidence_score": 0.90
    }
  ]
}

Text:
Jane Doe
Senior Engineer
"""
    assert rendered == expected


def test_match_insight_prompt_is_byte_identical() -> None:
    rendered = build_match_insight_prompt("Jane Doe profile", "python developer")
    expected = (
        "Given the candidate profile and resume text:\n"
        "Jane Doe profile\n\n"
        "Explain why this candidate is a good match for the search query: "
        "'python developer'. Output in bullet points in two sections: strengths and weaknesses (anything not matching/missing from the search query)."
    )
    assert rendered == expected


def test_match_insight_prompt_with_criteria() -> None:
    rendered = build_match_insight_prompt(
        "Jane Doe profile",
        "Python, React",
        city="San Francisco",
        job_title="Senior Engineer",
        min_years=5,
    )
    assert "Search Query / Skills: 'Python, React'" in rendered
    assert "Target Job Title: Senior Engineer" in rendered
    assert "Target City / Location: San Francisco" in rendered
    assert "Minimum Experience: 5 years" in rendered
    assert "Evaluate the candidate against all criteria above" in rendered


def test_match_insight_prompt_tolerates_braces_in_inputs() -> None:
    rendered = build_match_insight_prompt("{weird} {text}", "{query}")
    assert "{weird} {text}" in rendered
    assert "'{query}'" in rendered


def test_job_ad_distill_prompt_is_byte_identical() -> None:
    rendered = build_job_ad_distill_prompt("Hiring Backend Engineer in Berlin, 5+ years.")
    expected = """
You are a precise job-ad parser for a recruiting search engine.
Extract the structured requirements from the job advertisement below.

Return ONLY valid JSON with exactly these keys:
{
  "title": "<job title or null>",
  "skills": ["must-have skill", "..."],
  "min_yoe": <number of required years of experience or null>,
  "location": "<job location or null>"
}

Rules:
- Only include must-have requirements in "skills".
- "min_yoe" must be a plain number (e.g. 3 or 2.5) or null.
- Never invent values that are not stated in the ad.

Job advertisement:
Hiring Backend Engineer in Berlin, 5+ years.
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_is_byte_identical() -> None:
    rendered = build_consolidated_match_insight_prompt("Jane Doe profile", "python developer")
    expected = """
Given the candidate profile and resume text:
Jane Doe profile

Evaluate why this candidate is a good match for the following search criteria:
- Search Query / Skills: 'python developer'

Evaluate the candidate against all criteria above (job title, location/city, experience years, and required skills).
Please provide your evaluation in a clear, well-formatted markdown format.
Include the following sections:
- **Summary**: An executive summary of the match.
- **Strengths**: A bulleted list of strengths.
- **Weaknesses**: A bulleted list of weaknesses or missing required skills.
- **Match Confidence**: A score out of 10 or a percentage.
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_min_years_zero() -> None:
    rendered = build_consolidated_match_insight_prompt("Jane Doe profile", "python developer", min_years=0)
    assert "- Minimum Experience: 0 years" in rendered



def test_batched_extraction_prompt_is_byte_identical() -> None:
    rendered = build_batched_extraction_prompt(["Resume 1"])
    expected = """
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.
Return a list of results for each provided resume.
Return ONLY valid JSON matching this schema:
{
  "results": [
    {
      "claims": [
        ...
      ]
    }
  ]
}

Resumes:
Resume 1:
Resume 1
"""
    assert rendered == expected


def test_batched_extraction_prompt_multiple_resumes() -> None:
    rendered = build_batched_extraction_prompt(["Alice Doe\nPython Dev", "Bob Smith\nJava Dev"])
    assert "Resume 1:\nAlice Doe\nPython Dev" in rendered
    assert "Resume 2:\nBob Smith\nJava Dev" in rendered



def test_json_repair_prompt_is_byte_identical() -> None:
    rendered = build_json_repair_prompt('{"bad": json', "Expected quote")
    expected = """
You are a JSON repair engine.
The following JSON is malformed. Fix the syntax errors and return ONLY valid JSON matching the schema.
Do not add any explanations or markdown formatting outside the JSON block.

Malformed JSON:
{"bad": json

Error:
Expected quote
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_all_criteria() -> None:
    rendered = build_consolidated_match_insight_prompt(
        resume_text="Jane Doe profile",
        query="Python, AWS",
        city="London",
        job_title="Lead Architect",
        min_years=8,
    )
    assert "- Search Query / Skills: 'Python, AWS'" in rendered
    assert "- Target Job Title: Lead Architect" in rendered
    assert "- Target City / Location: London" in rendered
    assert "- Minimum Experience: 8 years" in rendered


def test_consolidated_match_insight_prompt_no_criteria() -> None:
    rendered = build_consolidated_match_insight_prompt(
        resume_text="Jane Doe profile",
        query="",
        city=None,
        job_title="",
        min_years=None,
    )
    assert "- (No specific criteria provided)" in rendered


def test_batched_extraction_prompt_three_resumes() -> None:
    resumes = [
        "Candidate One\nSkills: Go",
        "Candidate Two\nSkills: Rust",
        "Candidate Three\nSkills: TypeScript",
    ]
    rendered = build_batched_extraction_prompt(resumes)
    assert "Resume 1:\nCandidate One\nSkills: Go" in rendered
    assert "Resume 2:\nCandidate Two\nSkills: Rust" in rendered
    assert "Resume 3:\nCandidate Three\nSkills: TypeScript" in rendered


def test_json_repair_prompt_edge_cases() -> None:
    # Empty payload and empty error
    rendered_empty = build_json_repair_prompt("", "")
    assert "Malformed JSON:\n\n" in rendered_empty
    assert "Error:\n\n" in rendered_empty

    # Payload with special characters, quotes, and newlines
    payload = "{\n  \"key\": 'single quotes',\n  \"trailing\": 123,\n}"
    err = "Invalid character at line 2 col 10"
    rendered = build_json_repair_prompt(payload, err)
    assert payload in rendered
    assert err in rendered

