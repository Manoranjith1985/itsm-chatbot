"""LangGraph agent -- state machine definition."""
from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    messages: List[BaseMessage]
    user_id: str
    user_role: str
    ai_config: Dict[str, Any]
    itsm_configs: List[Dict[str, Any]]
    ai_write_enabled: bool
    pending_confirmation: Optional[Dict[str, Any]]
    chart_payload: Optional[Dict[str, Any]]


def input_parser(state: AgentState) -> AgentState:
    return state

def tool_router(state: AgentState) -> AgentState:
    return state

def tool_executor(state: AgentState) -> AgentState:
    return state

def confirmation_gate(state: AgentState) -> str:
    if state.get("pending_confirmation"):
        return "await_confirmation"
    return "tool_executor"

def response_formatter(state: AgentState) -> AgentState:
    return state


def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("input_parser", input_parser)
    graph.add_node("tool_router", tool_router)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("response_formatter", response_formatter)
    graph.set_entry_point("input_parser")
    graph.add_edge("input_parser", "tool_router")
    graph.add_conditional_edges(
        "tool_router", confirmation_gate,
        {"tool_executor": "tool_executor", "await_confirmation": END},
    )
    graph.add_edge("tool_executor", "response_formatter")
    graph.add_edge("response_formatter", END)
    return graph.compile()


agent_graph = build_agent_graph()
