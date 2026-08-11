from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set
import difflib

class ResolutionAction(Enum):
    NEW = "NEW"
    MERGE = "MERGE"
    REVIEW = "REVIEW"

@dataclass
class CandidateIdentifiers:
    candidate_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    full_name: str = ""

@dataclass
class ResolutionResult:
    action: ResolutionAction
    tier: int
    confidence: float
    matched_id: Optional[str] = None
    matching_keys: Set[str] = field(default_factory=set)

AUTO_MERGE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.70

def _normalize(name: str) -> str:
    return name.lower().strip()

def similarity_score(name1: str, name2: str) -> float:
    n1 = _normalize(name1)
    n2 = _normalize(name2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()

def resolve(incoming: CandidateIdentifiers, existing: List[CandidateIdentifiers]) -> ResolutionResult:
    if not existing:
        return ResolutionResult(action=ResolutionAction.NEW, tier=0, confidence=0.0)

    best_tier1_match = None
    best_tier1_keys = set()

    for cand in existing:
        matching_keys = set()
        if incoming.email and cand.email and incoming.email == cand.email:
            matching_keys.add("email")
        if incoming.phone and cand.phone and incoming.phone == cand.phone:
            matching_keys.add("phone")
        if incoming.linkedin_url and cand.linkedin_url and incoming.linkedin_url == cand.linkedin_url:
            matching_keys.add("linkedin_url")
        
        if matching_keys and len(matching_keys) > len(best_tier1_keys):
            best_tier1_keys = matching_keys
            best_tier1_match = cand

    if best_tier1_match:
        return ResolutionResult(
            action=ResolutionAction.MERGE,
            tier=1,
            confidence=1.0,
            matched_id=best_tier1_match.candidate_id,
            matching_keys=best_tier1_keys
        )

    if not incoming.full_name:
        return ResolutionResult(action=ResolutionAction.NEW, tier=0, confidence=0.0)

    best_tier2_match = None
    best_tier2_score = 0.0

    for cand in existing:
        score = similarity_score(incoming.full_name, cand.full_name)
        if score > best_tier2_score:
            best_tier2_score = score
            best_tier2_match = cand

    if best_tier2_match:
        if best_tier2_score >= AUTO_MERGE_THRESHOLD:
            return ResolutionResult(
                action=ResolutionAction.MERGE,
                tier=2,
                confidence=best_tier2_score,
                matched_id=best_tier2_match.candidate_id,
                matching_keys={"full_name"}
            )
        elif best_tier2_score >= REVIEW_THRESHOLD:
            return ResolutionResult(
                action=ResolutionAction.REVIEW,
                tier=2,
                confidence=best_tier2_score,
                matched_id=best_tier2_match.candidate_id,
                matching_keys={"full_name"}
            )

    return ResolutionResult(action=ResolutionAction.NEW, tier=0, confidence=0.0)
