# Idea: Autonomous Agentic Retrieval System

## Problem Statement
How might we allow recruiters to find highly specific, nuanced candidate profiles (e.g., "Led a team of 5+", "worked at a FinTech startup") without forcing them to write complex boolean queries or read through dozens of false-positive resumes?

## Recommended Direction
A multi-step Agentic Search pipeline. The user types a natural language query. The Agent autonomously calls database tools (Role/Location filters, Vector Search) to narrow the candidate pool down to a manageable shortlist. Then, the Agent uses a `read_raw_resume` tool to deeply analyze the remaining candidates, compare them against the nuanced requirements, and return the top matches with a qualitative explanation of *why* they fit. It runs autonomously but can occasionally ask clarifying questions if the initial prompt is too broad to filter.

## Key Assumptions to Validate
- [x] **Latency Tolerance:** Recruiters will tolerate a 15-30 second search latency if it means they don't have to read 50 resumes themselves.
- [x] **Funnel Accuracy:** Our initial tools (location/role/vector search) will be refined to be ultra-accurate to not drop the perfect candidate before the Agent reaches the "read raw text" phase.
- [x] **Judgment Alignment:** The LLM's reasoning on *why* candidate A is better than candidate B actually aligns with human recruiter preferences.

## MVP Scope
- 3 Tools provided to the Agent: `filter_by_metadata` (exact match), `vector_search` (semantic similarity), and `read_raw_resume` (full text analysis).
- Hardcoded limit: The agent is forced to narrow the pool to max 10 candidates before calling `read_raw_resume` to save cost/time.
- UI: A chat-like interface that shows the agent's "thinking" progress (e.g., "Searching for AI Engineers...", "Reading 8 resumes...") so the user knows it's working.
- State: The agent will support picking up where it left off (pagination/continuation) if the user asks to see more candidates.

## Not Doing (and Why)
- **Automated Outreach:** Too risky. The agent should find candidates, not talk to them.
- **Resume Scoring/Grading Numbers:** We won't output arbitrary scores (e.g., "92/100 match"). We will output qualitative reasoning, as arbitrary AI scores breed mistrust.
- **Highly Interactive Chat:** The agent won't ask questions on every step. It is optimized for autonomy to save the recruiter time.
