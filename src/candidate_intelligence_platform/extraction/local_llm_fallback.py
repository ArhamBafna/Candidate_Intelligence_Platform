import json
import ollama

def extract_inferences(text: str) -> list[dict]:
    """
    Extract AI inferences from text using a local LLM via Ollama.
    Expects Ollama to be running locally with the llama3 (or configured) model.
    """
    prompt = f"""
    You are a precise fact-extraction engine for resumes. 
    Extract the candidate's skills, job titles, and educational degrees from the following text.
    Return ONLY a JSON object with a 'claims' array. Each claim must have:
    - claim_category (e.g., SKILL, EMPLOYMENT, EDUCATION)
    - claim_key (e.g., Python, Senior Software Engineer)
    - claim_value (the explicit value)
    - confidence_score (a float between 0.0 and 1.0)
    
    Text:
    {text}
    """
    
    try:
        response = ollama.chat(model='llama3', messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ], format='json')
        
        content = response.message.content
        data = json.loads(content)
        
        claims = data.get("claims", [])
        facts = []
        for claim in claims:
            facts.append({
                "source_type": "AI_INFERENCE",
                "claim_category": claim.get("claim_category"),
                "claim_key": claim.get("claim_key"),
                "claim_value": claim.get("claim_value"),
                "confidence_score": float(claim.get("confidence_score", 0.9)),
                "source_char_offset_start": None,
                "source_char_offset_end": None,
                "extracted_by": "OLLAMA_LLM_V1"
            })
            
        return facts
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ollama inference failed. AI extraction will be skipped. Error: {e}")
        return []
