from pydantic import BaseModel, Field
from typing import List, Optional


class BotStateSchema(BaseModel):
    latest_query: str
    user_history: List[str]
    core_intent: Optional[str] = ""
    context_notes: Optional[str] = ""
    developer_task: Optional[str] = ""
    is_satisfied: Optional[bool] = False
    suggestions: Optional[List[str]] = Field(default_factory=list)
    communication_success: Optional[bool] = True
    enhancement_success: Optional[bool] = True

# -------------------------------
# CommunicationAgent Contracts
# -------------------------------

class CommunicationInput(BaseModel):
    user_query: str
    conversation_history: List[str]

class CommunicationOutput(BaseModel):
    core_intent: str
    context_notes: str
    success: bool = True
    message: str = "Intent extracted successfully"

# -------------------------------
# QueryRephraserAgent Contracts
# -------------------------------

class QueryEnhancerInput(BaseModel):
    core_intent: str
    context_notes: Optional[str] = None

class QueryEnhancerOutput(BaseModel):
    developer_task: str
    is_satisfied: bool
    suggestions: List[str] = Field(default_factory=list)
    success: bool = True
    message: str = "Query enhanced successfully"


