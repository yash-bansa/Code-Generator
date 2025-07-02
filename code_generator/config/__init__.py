"""
Configuration package for AI Code Generator
Contains settings and environment configurations
"""

from .settings import Settings, settings
from .agents_io import CommunicationInput, CommunicationOutput, QueryEnhancerInput,QueryEnhancerOutput

__all__ = [
    'CommunicationInput',
    'CommunicationOutput',
    'QueryEnhancerInput',
    'QueryEnhancerOutput',
    'Settings',
    'settings'
]