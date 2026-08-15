# research_graph.py - LangGraph definitions for the research workflow.
from langgraph.graph import StateGraph, END
from app.models.state import ResearchState
from app.agents.planner_agent import planner_node
from app.agents.search_agent import search_node
from app.agents.retrieval_agent import retrieval_node
from app.agents.analysis_agent import analysis_node
from app.agents.report_agent import report_node
from app.agents.evaluation_agent import evaluation_node
from app.core.config import settings

def create_research_graph():
    """
    Build the LangGraph orchestration for the AI Deep Research Agent.
    """
    # Initialize state graph
    workflow = StateGraph(ResearchState)
    
    # Add nodes representing modular agents
    workflow.add_node("planner", planner_node)
    workflow.add_node("search", search_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("report", report_node)
    workflow.add_node("evaluation", evaluation_node)
    
    # Define edges (linear path for now, easily expandable for loops later)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "search")
    workflow.add_edge("search", "retrieval")
    workflow.add_edge("retrieval", "analysis")
    workflow.add_edge("analysis", "report")
    if settings.SKIP_EVALUATION:
        workflow.add_edge("report", END)
    else:
        workflow.add_edge("report", "evaluation")
        workflow.add_edge("evaluation", END)
    
    # Compile graph
    return workflow.compile()
