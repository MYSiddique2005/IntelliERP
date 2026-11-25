"""Judging concept statements and rule values. No model decides a verdict.

    claim about a concept  ->  the concept's truth (a probe of the system's code, or a declared fact)  ->  compare

A claim whose concept is known is supported or contradicted; the verdict says what the system does. Rule values
are judged by the frozen TRACE verifier, imported unchanged.
"""
from app.llm.semantics.concepts import CONCEPTS
from app.llm.semantics.extract import ConceptClaim, concept_claims, rule_value_assertions
from app.llm.trace.schema import Verdict
from app.llm.trace.verify import verify as verify_assertion


def judge(claim: ConceptClaim) -> Verdict:
    concept = CONCEPTS[claim.key]
    actual = concept.holds
    status = "supported" if claim.holds == actual else "contradicted"
    shown = f"{'yes' if actual else 'no'}: {concept.evidence}"
    return Verdict(claim.quote, claim.key, "concept_holds", "semantic", "eq", f"eq {str(claim.holds).lower()}",
                   shown, status, concept.meaning, claim.origin)


class SemanticVerifier:
    """Checks what the assistant says about meanings. `source` (a TRACE FactSource, or any object with today()
    and separation_of_duties) lets rule values be judged; without it only concepts are."""

    def __init__(self, source=None, provider=None, role=None):
        self.source, self.provider, self.role = source, provider, role
        self.extraction = None

    def verdicts(self, text: str) -> list[Verdict]:
        claims = concept_claims(text)
        if self.provider is not None:
            from app.llm.semantics.extract_llm import extract
            self.extraction = extract(self.provider, text)
            claims += [c for c in self.extraction.claims if (c.key, c.holds) not in {(k.key, k.holds) for k in claims}]
        out = [judge(claim) for claim in claims]
        if self.source is not None:
            for assertion in rule_value_assertions(text):
                out.append(verify_assertion(assertion, self.source, self.role, origin="rule"))
        return out

    def contradicted(self, text: str) -> list[Verdict]:
        seen, unique = set(), []
        for verdict in self.verdicts(text):
            key = (verdict.attribute, verdict.subject, verdict.asserted)
            if verdict.status == "contradicted" and key not in seen:
                seen.add(key)
                unique.append(verdict)
        return unique
