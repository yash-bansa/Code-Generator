"""
Workflows Package - LangGraph Orchestration

This package contains the workflow orchestration logic using LangGraph
for processing pharmaceutical prescriptions through multiple AI agents.

The main workflow follows this sequence:
1. OCR: Extract text from prescription images
2. Extraction: Parse structured information from OCR text  
3. Structuring: Convert to validated data models
4. Coding: Assign clinical codes to medications
5. Export: Generate Excel output

Features:
- State-based workflow management
- Error handling and recovery
- Progress tracking and logging
- Modular agent integration
"""

from .processing_workflow import PharmaProcessingWorkflow

# Export main workflow class
__all__ = [
    "PharmaProcessingWorkflow"
]

# Workflow configuration constants
WORKFLOW_STEPS = [
    "ocr",
    "extraction", 
    "structuring",
    "coding",
    "excel_generation"
]

REQUIRED_METADATA_KEYS = [
    "ocr_completed",
    "extraction_completed",
    "structuring_completed", 
    "coding_completed",
    "excel_generated"
]

def create_workflow(lm_studio_client, **kwargs):
    """
    Factory function to create a configured workflow instance.
    
    Args:
        lm_studio_client: LM Studio client for agent communication
        **kwargs: Additional configuration options
        
    Returns:
        PharmaProcessingWorkflow instance
    """
    return PharmaProcessingWorkflow(lm_studio_client, **kwargs)

def get_workflow_info():
    """
    Get information about the workflow structure.
    
    Returns:
        dict: Workflow metadata and step information
    """
    return {
        "name": "PharmaProcessingWorkflow",
        "steps": WORKFLOW_STEPS,
        "total_steps": len(WORKFLOW_STEPS),
        "required_metadata": REQUIRED_METADATA_KEYS,
        "description": "AI-powered pharmaceutical prescription processing pipeline"
    }