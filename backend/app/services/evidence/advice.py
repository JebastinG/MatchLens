"""Truth-safe recommendations and interview questions (deterministic templates).

Recommendations never tell the user to claim a skill; they ask for accurate detail or point to
learning options. Templates are conditional ("if you have ...").
"""
from dataclasses import dataclass


@dataclass
class ReqView:
    ordinal: int
    text: str
    category: str
    status: str
    terms: list[str]
    quote: str | None  # verified evidence text for context, if any


def build_recommendations(views: list[ReqView]) -> list[tuple[int, str, str, int]]:
    """Return (ordinal, kind, text, priority). Lower priority number = shown first."""
    out = []
    for v in views:
        subj = ", ".join(v.terms) if v.terms else "this requirement"
        pri = 0 if v.category == "required" else 1
        if v.status == "needs_better_evidence":
            out.append((v.ordinal, "clarify_evidence",
                        f"Evidence for \"{v.text}\" is thin. If it is accurate, add the project or role, "
                        f"what you did with {subj}, and a measurable outcome.", pri))
        elif v.status == "related_skill_found":
            out.append((v.ordinal, "clarify_evidence",
                        f"Related experience was found but not {subj} itself. Describe the related work "
                        "accurately and how it transfers; do not claim direct experience you do not have.",
                        pri + 1))
        elif v.status == "no_evidence_found":
            out.append((v.ordinal, "add_evidence",
                        f"No evidence for \"{v.text}\" was found in the sources examined. If you do have "
                        "this experience, add it where it belongs. If not, it is a candidate learning "
                        "priority, not something to claim.", pri))
            if v.category == "required":
                out.append((v.ordinal, "learning_priority",
                            f"Consider a small, honest project or course covering {subj}.", 2))
        elif v.status == "uncertain":
            out.append((v.ordinal, "clarify_evidence",
                        f"The evidence for \"{v.text}\" was ambiguous. Review the retrieved passages and "
                        "make the relevant detail explicit if it is true.", pri + 1))
    out.sort(key=lambda r: (r[3], r[0]))
    return out


def build_questions(views: list[ReqView], limit: int = 10) -> list[tuple[int, str, str]]:
    order = {"needs_better_evidence": 0, "supported": 1, "related_skill_found": 2,
             "uncertain": 3, "no_evidence_found": 4}
    out = []
    for v in sorted(views, key=lambda v: (order[v.status], v.ordinal))[:limit]:
        if v.status == "supported":
            q = f"Walk through a specific example where you did this: \"{v.text}\". What was your role and the result?"
            why = "Your resume contains matching text; interviewers typically probe the details."
        elif v.status == "needs_better_evidence":
            q = f"Can you give a concrete example that shows: \"{v.text}\"?"
            why = "The resume mentions this but with little detail, so expect follow-up questions."
        elif v.status == "related_skill_found":
            q = f"How would you apply your related experience to: \"{v.text}\"?"
            why = "Only related experience was found; be ready to explain the transfer honestly."
        else:
            q = f"This role asks for: \"{v.text}\". What experience, if any, do you have with it?"
            why = "No clear evidence was found in the analyzed sources; this is a chance to clarify."
        out.append((v.ordinal, q, why))
    return out
