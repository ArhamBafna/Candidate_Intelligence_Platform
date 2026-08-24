# Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier)

## Problem Statement
Currently CIP uses Ollama for local LLM inference (generation tasks: candidate insights, job ad distillation, fallback extraction). OpenRouter offers OX Alpha model for free during promotional period. Switching could provide better quality generation without local GPU requirements.

## Proposed Change
Add a configurable toggle to switch between Ollama (local) and OpenRouter (cloud) for generation tasks:
- **Embeddings stay local** (no change to FastEmbed/SentenceTransformers)
- **Generation tasks** (chat_model, job_ad_distiller, local_llm_fallback, candidate insights) route through configurable backend
- **Graceful degradation**: Fall back to Ollama when offline or OpenRouter unavailable
- **Privacy note**: This introduces cloud dependency - document clearly for users

## Current Ollama Usage Points
- `src/candidate_intelligence_platform/intelligence/chat_model.py` - model listing/probing
- `src/candidate_intelligence_platform/search/job_ad_distiller.py` - job ad distillation
- `src/candidate_intelligence_platform/extraction/local_llm_fallback.py` - extraction fallback
- `api/routes/candidates.py` - streaming candidate insights

## Implementation Requirements
- [ ] Config schema: `llm_backend: "ollama" | "openrouter"` with OpenRouter API key
- [ ] Abstract LLM client interface behind common protocol
- [ ] OpenRouter client with OX Alpha model (openrouter/ox-alpha)
- [ ] Fallback chain: OpenRouter → Ollama → error
- [ ] Tests mock both backends (no live API calls in CI)
- [ ] Update AGENTS.md privacy note about optional cloud mode

## Risks
- **Privacy violation**: Cloud API sends candidate data to OpenRouter
- **Vendor lock-in**: Free tier may end; need migration path
- **Offline breakage**: Air-gapped deployments lose AI features without Ollama
- **Latency**: Network calls vs local inference

## Decision
Proceed as experimental toggle behind config flag. Default remains Ollama. Document privacy implications prominently.