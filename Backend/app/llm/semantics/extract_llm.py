"""Model extraction of concept statements: the text in, claims about named concepts out.

As in trace/extract_llm.py the model never says whether a claim is true. It records, for every sentence that
states what a term means or how two figures relate, which concept it is about and whether the sentence says it
holds. The concept list gives meanings but not truths.
"""
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from app.core.exceptions import ServiceUnavailableError
from app.llm.providers import Provider
from app.llm.semantics.concepts import CONCEPTS, catalogue_text
from app.llm.semantics.extract import ConceptClaim
from app.llm.tools import Tool
from app.security.permissions import Permission

RECORD_TOOL = "record_concepts"
PROMPT_VERSION = "semantics-extract-1"
KEYS = tuple(CONCEPTS)


class ConceptItem(BaseModel):
    quote: str = Field(min_length=1, max_length=400, description="The exact words of the statement")
    concept: str = Field(description="One concept key from the list")
    holds: bool = Field(description="true if the text says the concept holds; false if the text says it does not")


class ConceptList(BaseModel):
    claims: list[ConceptItem] = Field(default_factory=list, max_length=40)


def system_prompt() -> str:
    return (
        "You find statements in a text, written by an ERP assistant, about what the system's own terms mean or how its "
        "figures relate. For each one, record which concept from the list it is about and whether the text says the "
        "concept holds. You never decide whether the statement is true and never correct it: if the text says overdue "
        "units are part of the units on order, record holds=true for that concept, whatever you believe. Record a "
        "statement only when it is clearly about one listed concept; skip advice, figures about a particular product "
        "and anything you would have to guess. Use holds=false when the text says the concept does not hold ('not "
        "back-ordered').\n\nConcepts:\n" + catalogue_text() + "\n\nCall record_concepts once with every such statement "
        "(an empty list if there is none)."
    )


def record_tool() -> Tool:
    return Tool(RECORD_TOOL, "Record every statement about a listed concept (an empty list if none).",
                Permission.AI_USE, ConceptList, lambda arguments: arguments)


@dataclass
class ConceptExtraction:
    claims: list[ConceptClaim]
    invalid: int = 0
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


def extract(provider: Provider, text: str) -> ConceptExtraction:
    try:
        conversation = provider.start(system_prompt(), [record_tool()], [], f"<text>\n{text}\n</text>", require_tool=True)
        reply = conversation.reply()
    except ServiceUnavailableError as error:
        return ConceptExtraction([], error=getattr(error, "message", str(error)))
    result = ConceptExtraction([], input_tokens=reply.input_tokens, output_tokens=reply.output_tokens)
    call = next((c for c in reply.tool_calls if c.name == RECORD_TOOL), None)
    if call is None:
        return result
    items = call.arguments.get("claims") or []
    for item in items if isinstance(items, list) else []:
        try:
            parsed = ConceptItem.model_validate(item)
        except ValidationError:
            result.invalid += 1
            continue
        if parsed.concept in CONCEPTS:
            result.claims.append(ConceptClaim(parsed.concept, parsed.holds, parsed.quote, origin="model"))
        else:
            result.invalid += 1
    return result
