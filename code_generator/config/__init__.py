"""
Configuration package for AI Code Generator
Contains settings and environment configurations
"""

from .settings import Settings, settings
from .agents_io import (
    BotStateSchema,
    CommunicationInput, 
    CommunicationOutput, 
    QueryEnhancerInput,
    QueryEnhancerOutput,
    MasterPlannerInput,
    MasterPlannerOutput,
    SuggestedChange )

__all__ = [
    'CommunicationInput',
    'CommunicationOutput',
    'QueryEnhancerInput',
    'QueryEnhancerOutput',
    'MasterPlannerInput',
    'MasterPlannerOutput',
    'SuggestedChange',
    'BotStateSchema',
    'Settings',
    'settings'
]