# Idea: Autonomous Agentic Retrieval System

Product direction only. This document preserves the proposed scope; implementation should turn assumptions into measured experiments before treating them as requirements.

## Problem Statement
How might we allow recruiters to find highly specific, nuanced candidate profiles (e.g., "Led a team of 5+", "worked at a FinTech startup") without forcing them to write complex boolean queries or read through dozens of false-positive resumes?

## Recommended Direction
A multi-step Agentic Search pipeline. The user types a natural language query. The Agent autonomously calls database tools (Role/Location filters, Vector Search) to narrow the candidate pool down to a manageable shortlist. Then, the Agent uses a `read_raw_resume` tool to deeply analyze the remaining candidates, compare them against the nuanced requirements, and return the top matches with a qualitative explanation of *why* they fit. It runs autonomously but can occasionally ask clarifying questions if the initial prompt is too broad to filter.

## Key Assumptions to Validate

These are hypotheses, not completed validation. Mark each checked only after recording evidence and its evaluation method.

- [ ] **Latency tolerance:** Test whether recruiters accept 15–30 second searches when this avoids reading 50 résumés. Record acceptance rate and sample size.
- [ ] **Funnel accuracy:** Measure recall of location, role, and vector filters against a labelled candidate set before raw-text analysis. Record candidates lost before the `read_raw_resume` phase.
- [ ] **Judgment alignment:** Compare qualitative explanations and rankings with recruiter judgments on the same candidate set. Record agreement and disagreement themes.

## MVP Scope
- 3 tools provided to the Agent: `filter_by_metadata` (exact match), `vector_search` (semantic similarity), and `read_raw_resume` (full text analysis).
- Hardcoded limit: the Agent narrows the pool to at most 10 candidates before calling `read_raw_resume` to save cost/time.
- UI: A chat-like interface that shows the agent's "thinking" progress (e.g., "Searching for AI Engineers...", "Reading 8 resumes...") so the user knows it's working.
- State: The agent will support picking up where it left off (pagination/continuation) if the user asks to see more candidates.

MVP is complete when all three tools have defined inputs and outputs, the 10-candidate guard is enforced, progress states are user-visible, and continuation returns the next result set without losing prior context.

## Not doing (and why)
- **Automated Outreach:** Too risky. The agent should find candidates, not talk to them.
- **Resume Scoring/Grading Numbers:** We won't output arbitrary scores (e.g., "92/100 match"). We will output qualitative reasoning, as arbitrary AI scores breed mistrust.
- **Highly Interactive Chat:** The agent won't ask questions on every step. It is optimized for autonomy to save the recruiter time.
