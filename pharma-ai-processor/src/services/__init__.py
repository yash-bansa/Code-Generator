"""
Services module for pharma AI processor.
Contains core services for LM Studio integration and Excel generation.
"""

from .lm_studio_client import LMStudioClient
from .excel_generator import ExcelGenerator

__all__ = [
    'LMStudioClient',
    'ExcelGenerator'
]