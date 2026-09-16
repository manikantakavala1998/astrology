"""Orchestrates a single question -> answer turn: retrieve relevant
knowledge-base passages, combine with the exact computed chart facts, and
ask the local LLM - the "act like an astrologer" feature.
"""

from __future__ import annotations

from datetime import datetime

from vedic_astro.models import KundaliChart, MatchReport
from vedic_astro.rag.chart_summary import summarize_chart, summarize_match
from vedic_astro.rag.embeddings import embed
from vedic_astro.rag.knowledge_base import query as query_knowledge_base
from vedic_astro.rag.llm import chat

_SYSTEM_PROMPT_TEMPLATE = """You are a Vedic astrology assistant. Answer the \
user's question using the CHART FACTS and REFERENCE NOTES below - both are \
supplied to you, do not invent placements, dates, or rules that aren't given.

If the reference notes don't cover something, say so plainly rather than \
guessing. Keep answers grounded, concise, and specific to this chart - refer \
to the actual planets, houses, and periods given below rather than speaking \
in generalities.

=== CHART FACTS (exact, computed) ===
{chart_facts}

=== REFERENCE NOTES (general classical astrology background, may or may \
not be directly relevant) ===
{reference_notes}
"""

TOP_K_DEFAULT = 5


def answer_question(
    question: str,
    chart: KundaliChart,
    match_report: MatchReport | None = None,
    reference_datetime: datetime | None = None,
    top_k: int = TOP_K_DEFAULT,
) -> str:
    reference_datetime = reference_datetime or datetime.now()

    chart_facts = summarize_chart(chart, reference_datetime)
    if match_report is not None:
        chart_facts = f"{chart_facts}\n\n{summarize_match(match_report)}"

    question_embedding = embed(question)
    retrieved = query_knowledge_base(question_embedding, top_k=top_k)
    reference_notes = "\n\n".join(retrieved) if retrieved else "(no relevant reference notes found)"

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(chart_facts=chart_facts, reference_notes=reference_notes)
    return chat(system_prompt=system_prompt, user_message=question)
