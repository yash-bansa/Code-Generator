from pydantic import BaseModel, Field
from typing import Dict,Any,List, Optional, Literal
from pathlib import Path




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


# -------------------------------
# Master Planner Agent Contracts
# -------------------------------  


class MasterPlannerInput(BaseModel):
    parsed_config: Dict[str, Any]
    project_path: Path
    user_question: str


class SuggestedChange(BaseModel):
    type: Literal["add_function", "modify_function", "add_import", "modify_variable"]
    target: str
    description: str


class CrossFileDependency(BaseModel):
    source_file: str
    target_file: str
    linked_element: str
    type: Literal["function_usage", "class_usage", "variable_usage"]
    reason: str


class FileAnalysisResult(BaseModel):
    needs_modification: bool
    modification_type: Optional[
        Literal["data_loading", "data_transformation", "output_handling", "configuration", "utility"]
    ] = ""
    priority: Literal["high", "medium", "low"] = "low"
    reason: str
    suggested_changes: List[SuggestedChange] = Field(default_factory=list)
    cross_file_dependencies: List[CrossFileDependency] = Field(default_factory=list)


class TargetFileOutput(BaseModel):
    file_path: str
    file_info: Dict[str, Any]
    structure: Dict[str, Any]
    analysis: FileAnalysisResult
    priority: Literal["high", "medium", "low"]


class MasterPlannerOutput(BaseModel):
    success: bool
    message: str
    files_to_modify: List[TargetFileOutput] = Field(default_factory=list)

# -------------------------------
# Delta Analyzer Agent Contracts
# -------------------------------  

class Modification(BaseModel):
    action: str
    target_type: str
    target_name: str
    line_number: Optional[int] = 0
    old_code: Optional[str] = ""
    new_code: str
    explanation: str
    affects_dependencies: Optional[List[str]] = Field(default_factory=list)  # KEEP

class DeltaAnalyzerInput(BaseModel):
    file_path: str
    file_content: str
    file_analysis: Dict[str, Any]  # Contains cross_dependencies already
    config: Dict[str, Any]
    # NO additional fields needed - keep it clean

class DeltaAnalyzerOutput(BaseModel):
    modifications: List[Modification]
    new_dependencies: List[str] = Field(default_factory=list)
    testing_suggestions: List[str] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)
    cross_file_impacts: Optional[List[str]] = Field(default_factory=list)      # KEEP
    implementation_notes: Optional[List[str]] = Field(default_factory=list)    # KEEP


class BotStateSchema(BaseModel):
    latest_query: str
    user_history: List[str]
    
    # Communication Agent Output
    core_intent: Optional[str] = ""
    context_notes: Optional[str] = ""
    communication_success: bool = False
    
    # Query Rephraser Agent Output
    developer_task: Optional[str] = ""
    is_satisfied: bool = False
    suggestions: List[str] = []
    enhancement_success: bool = False
    
    # Master Planner Agent Output
    master_planner_success: bool = False
    master_planner_message: Optional[str] = ""
    master_planner_result: List[TargetFileOutput] = Field(default_factory=list)
    parsed_config: Optional[Dict[str, Any]] = Field(default_factory=dict)  # NEW: Store parsed config for Delta Analyzer
    
    # Delta Analyzer Agent Output - NEW SECTION
    delta_analyzer_success: bool = False
    delta_analyzer_message: Optional[str] = ""
    modification_plan: Optional[Dict[str, Any]] = Field(default_factory=dict)