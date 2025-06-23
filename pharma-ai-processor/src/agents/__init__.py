"""
Agents Package - Core Processing Agents

This package contains the specialized AI agents responsible for different
stages of prescription processing in the agentic workflow.

Agents:
- OCRAgent: Optical Character Recognition using Vision Language Models
- ExtractionAgent: Information extraction from raw OCR text
- StructuringAgent: Data structuring and validation
- CodingAgent: Clinical code assignment for medications/procedures

Each agent is designed to be:
- Stateless and reusable
- Error-resistant with proper exception handling
- Focused on a single responsibility
- Compatible with LangGraph workflow orchestration
"""

from .ocr_agent import OCRAgent
from .extraction_agent import ExtractionAgent
from .structuring_agent import StructuringAgent
from .coding_agent import CodingAgent

# Export all agents for easy importing
__all__ = [
    "OCRAgent",
    "ExtractionAgent", 
    "StructuringAgent",
    "CodingAgent"
]

# Agent metadata for workflow orchestration
AGENT_REGISTRY = {
    "ocr": OCRAgent,
    "extraction": ExtractionAgent,
    "structuring": StructuringAgent,
    "coding": CodingAgent
}

def get_agent(agent_name: str, *args, **kwargs):
    """
    Factory function to create agent instances by name.
    
    Args:
        agent_name: Name of the agent to create
        *args, **kwargs: Arguments to pass to agent constructor
        
    Returns:
        Agent instance
        
    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name not in AGENT_REGISTRY:
        available_agents = ", ".join(AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent '{agent_name}'. Available agents: {available_agents}")
    
    agent_class = AGENT_REGISTRY[agent_name]
    return agent_class(*args, **kwargs)