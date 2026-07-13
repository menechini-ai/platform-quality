"""LangGraph agent pipeline — multi-step agent orchestration for ObservAI.

Uses the dual-LLM pattern:
- ``get_reasoning_model()`` (gpt-4o) for triage/analysis.
- ``get_tool_model()`` (gpt-4o-mini) for runbook recommendations.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.dual_llm import get_reasoning_model, get_tool_model

# ── State ──────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: list[dict[str, str]]
    incident_id: str | None
    analysis: str | None
    recommendation: str | None


# ── Nodes ──────────────────────────────────────────────────────────────


async def triage_incident(state: AgentState) -> dict[str, Any]:
    llm = get_reasoning_model()
    prompt = f"Triage incident {state.get('incident_id', 'unknown')}:\n{state['messages'][-1]['content']}"
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"analysis": resp.content}


async def generate_recommendation(state: AgentState) -> dict[str, Any]:
    llm = get_tool_model()
    prompt = f"Based on analysis:\n{state.get('analysis', '')}\n\nSuggest a runbook action."
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"recommendation": resp.content}


def should_continue(state: AgentState) -> Literal["generate_recommendation", "__end__"]:
    return "generate_recommendation" if state.get("analysis") else "__end__"


# ── Graph ──────────────────────────────────────────────────────────────


def build_pipeline() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("triage_incident", triage_incident)
    graph.add_node("generate_recommendation", generate_recommendation)

    graph.add_edge(START, "triage_incident")
    graph.add_conditional_edges("triage_incident", should_continue)
    graph.add_edge("generate_recommendation", END)

    return graph.compile()


async def run_pipeline(incident_id: str, description: str) -> AgentState:
    pipeline = build_pipeline()
    initial: AgentState = {
        "messages": [{"role": "user", "content": description}],
        "incident_id": incident_id,
        "analysis": None,
        "recommendation": None,
    }
    return await pipeline.ainvoke(initial)


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Run the LangGraph incident pipeline")
    parser.add_argument("--incident", required=True, help="Incident description")
    parser.add_argument("--id", default="cli-incident", help="Incident ID (default: cli-incident)")
    args = parser.parse_args()

    result = asyncio.run(run_pipeline(incident_id=args.id, description=args.incident))
    print(f"Incident: {args.id}")
    print(f"Analysis: {result.get('analysis', 'N/A')}")
    print(f"Recommendation: {result.get('recommendation', 'N/A')}")
