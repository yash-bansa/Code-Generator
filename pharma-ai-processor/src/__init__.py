"""
Pharma AI Processor - Core Package

A proof-of-concept AI solution for processing pharmaceutical prescriptions and bills
using agentic AI architecture with LangGraph and LM Studio.

Main Components:
- OCR Agent: Extracts text from prescription images using VLMs
- Extraction Agent: Extracts structured information from OCR text
- Structuring Agent: Converts extracted data to structured format
- Coding Agent: Assigns clinical codes to medications/procedures
- Excel Generator: Creates structured Excel output

Version: 0.1.0 (Proof of Concept)
"""

__version__ = "0.1.0"
__author__ = "AI Engineering Team"
__description__ = "AI-powered pharmaceutical prescription processing system"

# Core components
from .schemas import ProcessingState, PrescriptionData, LineItem

# Make key classes available at package level
__all__ = [
    "ProcessingState",
    "PrescriptionData", 
    "LineItem"
]