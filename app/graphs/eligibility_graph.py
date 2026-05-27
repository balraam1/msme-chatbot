# app/graphs/eligibility_graph.py
from typing import TypedDict, Dict, Optional, List, Any
from langgraph.graph import StateGraph, START, END

# Define state schema
class EligibilityState(TypedDict):
    session_id: str
    answers: Dict[str, str]
    next_question: Optional[str]
    last_message: str
    reply: str
    complete: bool

def check_next_question(state: EligibilityState) -> EligibilityState:
    answers = state.get("answers", {})
    required = ["role", "state", "gender", "category", "venture", "biz_type", "cost"]
    
    prompts = {
        "role": "Are you a Student, Entrepreneur, or Business Owner?",
        "state": "What state do you reside in?",
        "gender": "What is your gender?",
        "category": "What is your social category (General/SC/ST/OBC/EBC/Minority/PwD)?",
        "venture": "Is your business/venture new or existing?",
        "biz_type": "What is your business type (Manufacturing/Agro/Tech-Innovation/Service/Other)?",
        "cost": "What is your project/venture cost or funding requirement (in Rupees)?"
    }
    
    for field in required:
        if not answers.get(field):
            return {
                **state,
                "next_question": field,
                "reply": prompts[field],
                "complete": False
            }
            
    return {
        **state,
        "next_question": None,
        "complete": True
    }

def process_answer(state: EligibilityState) -> EligibilityState:
    answers = state.get("answers", {}).copy()
    current_q = state.get("next_question")
    user_input = state.get("last_message", "").strip()
    
    if current_q and user_input:
        # Save user response for the current question
        answers[current_q] = user_input
        
    return {
        **state,
        "answers": answers,
        "last_message": ""
    }

def generate_recommendation(state: EligibilityState) -> EligibilityState:
    answers = state.get("answers", {})
    # Construct a RAG query
    rag_query = (
        f"{answers.get('role')} from {answers.get('state')}, {answers.get('gender')}, "
        f"{answers.get('category')} category, {answers.get('venture')} {answers.get('biz_type')} business "
        f"with project cost {answers.get('cost')}."
    )
    
    from app.knowledge_base import retrieve_context
    context = retrieve_context(rag_query, k=4)
    
    from app.llm import get_chat_response
    user_msg = (
        f"Based on the collected details: {answers}, please recommend the best matching MSME government schemes "
        f"and calculate specific subsidies. Focus on eligibility. Context: {context}"
    )
    
    structured_res = get_chat_response(
        user_message=user_msg,
        conversation_history=[],
        rag_context=context,
        is_voice_mode=False
    )
    
    reply = structured_res.get("raw") or structured_res.get("next_step") or "No recommendations found."
    return {
        **state,
        "reply": reply,
        "complete": True
    }

# Build workflow
workflow = StateGraph(EligibilityState)
workflow.add_node("check_next", check_next_question)
workflow.add_node("process", process_answer)
workflow.add_node("recommend", generate_recommendation)

workflow.add_edge(START, "check_next")

def route_next(state: EligibilityState):
    if state.get("complete"):
        return "recommend"
    else:
        return END

workflow.add_conditional_edges("check_next", route_next, {
    "recommend": "recommend",
    END: END
})
workflow.add_edge("process", "check_next")
workflow.add_edge("recommend", END)

eligibility_graph = workflow.compile()
