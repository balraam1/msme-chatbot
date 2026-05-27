# app/session_graph.py
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

# Define state schema
class SessionState(TypedDict):
    session_id: str
    messages: List[Dict[str, str]]
    last_message: str
    reply: str
    structured: Optional[Dict]

def get_session_reply(state: SessionState) -> SessionState:
    session_id = state.get("session_id", "default")
    last_msg = state.get("last_message", "")
    history = state.get("messages", [])
    
    # Pre-process message (safety, scrub)
    from app.content_filter import is_blocked
    blocked, reason = is_blocked(last_msg)
    if blocked:
        return {
            **state,
            "reply": "This query cannot be processed on this platform.",
            "structured": {
                "intent": "out_of_scope",
                "items": [],
                "next_step": "",
                "disclaimer": "Safety filter blocked content. Please ask a question related to MSME schemes."
            }
        }
        
    # Retrieve RAG context
    from app.knowledge_base import retrieve_context
    rag_context = retrieve_context(last_msg, k=3)
    
    # Get LLM response
    from app.llm import get_chat_response
    structured = get_chat_response(
        user_message=last_msg,
        conversation_history=history,
        rag_context=rag_context,
        is_voice_mode=False
    )
    
    # Update history in state
    updated_messages = history.copy()
    updated_messages.append({"role": "user", "content": last_msg})
    updated_messages.append({"role": "assistant", "content": structured.get("raw") or structured.get("next_step", "")})
    
    return {
        **state,
        "messages": updated_messages[-20:], # limit to 20 window
        "reply": structured.get("raw") or structured.get("next_step", ""),
        "structured": structured
    }

# Build workflow
workflow = StateGraph(SessionState)
workflow.add_node("chat", get_session_reply)
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)

session_graph = workflow.compile()
