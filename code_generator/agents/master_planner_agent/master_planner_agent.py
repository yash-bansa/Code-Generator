import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml
from pydantic import ValidationError
from config.agents_io import (
    MasterPlannerInput,
    MasterPlannerOutput,
    TargetFileOutput,
    SuggestedChange,
    FileAnalysisResult,
    CrossFileDependency
)
from utils.file_handler import FileHandler
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MasterPlannerAgent:
    def __init__(self):
        config_path = Path(__file__).parent / "master_planner_config.yaml"
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            self.system_prompt = config.get("system_prompt", "You are a Code Identifier Agent.")
        except Exception as e:
            logger.error(f"[MasterPlannerAgent] Failed to load system prompt: {e}")
            self.system_prompt = "You are a Code Identifier Agent."
    
    async def identify_target_files(self, input_data: MasterPlannerInput) -> MasterPlannerOutput:
        logger.info("🔍 Starting file identification process...")
        
        if not input_data.project_path.exists():
            return MasterPlannerOutput(
                success=False,
                message="Project path does not exist.",
                files_to_modify=[]
            )
        
        # ✅ Extract specific file mentions from user question
        specific_files = self._extract_specific_files(input_data.user_question)
        logger.info(f"📝 Specific files mentioned: {specific_files}")
        
        # ✅ Validate specific files exist if mentioned
        if specific_files:
            validation_result = self._validate_specific_files(specific_files, input_data.project_path)
            if not validation_result["valid"]:
                return MasterPlannerOutput(
                    success=False,
                    message=validation_result["message"],
                    files_to_modify=[]
                )
        
        target_files = []
        
        try:
            # ✅ Get files to analyze (specific files if mentioned, otherwise all)
            if specific_files:
                files_to_analyze = self._get_specific_file_paths(specific_files, input_data.project_path)
                logger.info(f"🎯 Analyzing specific files: {[str(f) for f in files_to_analyze]}")
            else:
                files_to_analyze = FileHandler.find_files(input_data.project_path, ['.py'])
                logger.info(f"📁 Analyzing all Python files: {len(files_to_analyze)} files")
            
            # Process each file
            for file_path in files_to_analyze:
                try:
                    # ✅ Validate file_path is valid
                    if not file_path or not isinstance(file_path, Path):
                        logger.warning(f"Invalid file_path: {file_path}")
                        continue
                    
                    file_info = FileHandler.get_file_info(file_path)
                    file_structure = FileHandler.parse_python_file(file_path)
                    file_content = FileHandler.read_file(file_path)
                    
                    if file_structure and isinstance(file_content, str):
                        analysis = await self._analyze_file_relevance(
                            file_path,
                            file_content,
                            file_structure,
                            input_data.parsed_config,
                            input_data.user_question,
                            is_specifically_mentioned=file_path.name in specific_files
                        )
                        
                        if analysis.needs_modification:
                            # ✅ Ensure file_path is always a valid string
                            file_path_str = str(file_path.resolve())
                            logger.info(f"✅ Adding file for modification: {file_path_str}")
                            
                            target_files.append(TargetFileOutput(
                                file_path=file_path_str,
                                file_info=file_info,
                                structure=file_structure,
                                analysis=analysis,
                                priority=analysis.priority or "medium"
                            ))
                        else:
                            logger.info(f"❌ File doesn't need modification: {file_path.name}")
                            
                except Exception as fe:
                    logger.error(f"[FILE ERROR] Failed to process {file_path}: {fe}")
                    continue
            
            # ✅ Debug logging
            logger.info(f"📊 Total files processed: {len(files_to_analyze)}")
            logger.info(f"📊 Files needing modification: {len(target_files)}")
            
            # Prioritize files
            priority_order = {"high": 3, "medium": 2, "low": 1}
            target_files.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=True)
            
            # ✅ Final validation - if specific files mentioned, ensure they're in results
            if specific_files:
                found_file_names = []
                for i, tf in enumerate(target_files):
                    try:
                        if hasattr(tf, 'file_path') and tf.file_path and isinstance(tf.file_path, str) and tf.file_path.strip():
                            file_name = Path(tf.file_path).name
                            found_file_names.append(file_name)
                            logger.debug(f"Found file in results: {file_name}")
                        else:
                            logger.warning(f"Target file[{i}] has invalid file_path: '{tf.file_path}' (type: {type(tf.file_path)})")
                    except Exception as e:
                        logger.error(f"Error processing target_files[{i}]: {e}")
                        continue
                
                logger.info(f"🔍 Found files in results: {found_file_names}")
                logger.info(f"🎯 Expected specific files: {specific_files}")
                
                missing_specific_files = [f for f in specific_files if f not in found_file_names]
                
                if missing_specific_files:
                    return MasterPlannerOutput(
                        success=False,
                        message=f"Specifically mentioned files were not identified for modification: {', '.join(missing_specific_files)}. Either they don't need changes or analysis failed.",
                        files_to_modify=[]
                    )
            
            # ✅ Check if any files were found
            if not target_files:
                if specific_files:
                    return MasterPlannerOutput(
                        success=False,
                        message=f"No modifications needed for the specifically mentioned files: {', '.join(specific_files)}",
                        files_to_modify=[]
                    )
                else:
                    return MasterPlannerOutput(
                        success=False,
                        message="No files identified for modification based on the requirements.",
                        files_to_modify=[]
                    )
            
        except Exception as e:
            logger.exception(f"❌ Unexpected error during file identification: {e}")
            return MasterPlannerOutput(
                success=False,
                message=f"Unexpected error during file scan: {str(e)}",
                files_to_modify=[]
            )
        
        logger.info(f"✅ Successfully identified {len(target_files)} files for modification")
        return MasterPlannerOutput(
            success=True,
            message=f"Successfully identified {len(target_files)} files for modification.",
            files_to_modify=target_files
        )
    
    def _extract_specific_files(self, user_question: str) -> List[str]:
        """Extract specific file names mentioned in the user question."""
        logger.info(f"Extracting files from query: '{user_question}'")
        
        # Enhanced patterns to match file names with extensions
        file_patterns = [
            # Direct file mentions
            r'\b(\w+\.py)\b',                           # filename.py
            r'["\']([^"\']*\.py)["\']',                 # "filename.py" or 'filename.py'
            
            # Contextual file mentions
            r'\bin\s+(?:the\s+)?["\']?(\w+\.py)["\']?',      # in [the] filename.py
            r'\bfrom\s+(?:the\s+)?["\']?(\w+\.py)["\']?',    # from [the] filename.py
            r'\bfile\s+["\']?(\w+\.py)["\']?',               # file filename.py
            r'\bto\s+(?:the\s+)?["\']?(\w+\.py)["\']?',      # to [the] filename.py
            r'\bmodify\s+(?:the\s+)?["\']?(\w+\.py)["\']?',  # modify [the] filename.py
            r'\bupdate\s+(?:the\s+)?["\']?(\w+\.py)["\']?',  # update [the] filename.py
            r'\bedit\s+(?:the\s+)?["\']?(\w+\.py)["\']?',    # edit [the] filename.py
            
            # Handle phrases like "dataframe in the data_loader.py"
            r'\b(?:dataframe|data|code|function|class)\s+in\s+(?:the\s+)?["\']?(\w+\.py)["\']?',
        ]
        
        specific_files = set()
        
        for i, pattern in enumerate(file_patterns):
            try:
                matches = re.findall(pattern, user_question, re.IGNORECASE)
                if matches:
                    logger.debug(f"Pattern {i+1} matched: {matches}")
                    specific_files.update(matches)
            except Exception as e:
                logger.warning(f"Error in pattern {i+1}: {e}")
                continue
        
        # Remove common false positives and invalid entries
        false_positives = {'__init__.py', 'setup.py', 'conftest.py'}
        specific_files = specific_files - false_positives
        
        # Additional validation: ensure files end with .py and are valid filenames
        valid_files = []
        for file_name in specific_files:
            if (file_name.endswith('.py') and 
                len(file_name) > 3 and  # More than just ".py"
                re.match(r'^[\w\-\.]+\.py$', file_name)):  # Valid filename pattern
                valid_files.append(file_name)
            else:
                logger.debug(f"Filtered out invalid filename: '{file_name}'")
        
        logger.info(f"Final extracted files: {valid_files}")
        return valid_files
    
    def _validate_specific_files(self, specific_files: List[str], project_path: Path) -> Dict[str, Any]:
        """Validate that specifically mentioned files exist in the project."""
        missing_files = []
        available_files = [f.name for f in project_path.rglob("*.py")]
        
        logger.info(f"Available files in project: {available_files}")
        
        for file_name in specific_files:
            file_found = False
            # Check if file exists in project directory or subdirectories
            for existing_file in project_path.rglob("*.py"):
                if existing_file.name == file_name:
                    file_found = True
                    logger.info(f"✅ Found specific file: {file_name}")
                    break
            
            if not file_found:
                missing_files.append(file_name)
                logger.warning(f"❌ Missing specific file: {file_name}")
        
        if missing_files:
            return {
                "valid": False,
                "message": f"Specifically mentioned files not found in project: {', '.join(missing_files)}. Available files: {', '.join(available_files)}"
            }
        
        return {"valid": True, "message": "All specific files found"}
    
    def _get_specific_file_paths(self, specific_files: List[str], project_path: Path) -> List[Path]:
        """Get full paths for specifically mentioned files."""
        file_paths = []
        
        for file_name in specific_files:
            for existing_file in project_path.rglob("*.py"):
                if existing_file.name == file_name:
                    file_paths.append(existing_file)
                    logger.info(f"📁 Found path for {file_name}: {existing_file}")
                    break
        
        return file_paths
    
    async def _analyze_file_relevance(
        self,
        file_path: Path,
        content: str,
        structure: Dict[str, Any],
        config: Dict[str, Any],
        user_question: str,
        is_specifically_mentioned: bool = False
    ) -> FileAnalysisResult:
        if not all([file_path, content, structure, config, user_question]):
            logger.error("Invalid inputs to _analyze_file_relevance.")
            return self._default_analysis()
        
        # ✅ Enhanced context for specifically mentioned files
        specificity_context = ""
        if is_specifically_mentioned:
            specificity_context = f"""
IMPORTANT: This file ({file_path.name}) was SPECIFICALLY MENTIONED by the user in their request.
Give it HIGH PRIORITY and ensure modifications are applied here unless technically impossible.
"""
        
        prompt = f"""
Analyze this Python file to determine if it needs modification based on the configuration:

File: {file_path.name}
{specificity_context}

File Structure:
- Functions: {[f['name'] for f in structure.get('functions', [])]}
- Classes: {[c['name'] for c in structure.get('classes', [])]}
- Imports: {structure.get('imports', [])}

Configuration Requirements:
{json.dumps(config, indent=2)}

User Request:
"{user_question}"

File Content (first 1000 chars):
{content[:1000]}

Determine:
1. Does this file need modification? (yes/no)
2. What type of modifications are needed?
3. What is the priority level? (high/medium/low)
4. What specific changes should be made?

Additional Instructions:
- If this file was specifically mentioned by the user, prioritize it as HIGH unless there's no technical relevance
- Carefully trace dependencies across files using the transformation chain
- If a function in one file produces output needed in another file, mark that explicitly
- For example: if `load_customers()` from `data_loader.py` produces input for `join_customer_sales()` in `data_transformer.py`, include that in your analysis
- Reflect such dependencies clearly using a "cross_file_dependencies" key in the output if applicable
- If the user request explicitly refers to a specific file (e.g., "add ranking logic to data_loader.py"), prioritize applying modifications in that file only
- Avoid duplicating logic such as transformations, filtering, ranking, or feature engineering across multiple files
- Apply transformations or changes as close as possible to the data origin or logical owner of the process
- Only modify additional files if:
    - The logic added affects their operation (e.g., a function's output schema changes)
    - They explicitly depend on or consume updated components (e.g., via import or data flow)
    - Failing to modify them would break pipeline integrity or user intent
- When in doubt, prefer centralizing new logic in the file the user mentioned or where the data is first introduced
- Strictly follow the user instruction never add any additional data or code by your own be on the user demand avoid adding extra coding

Return JSON:
{{
  "needs_modification": true/false,
  "modification_type": "data_loading|data_transformation|output_handling|configuration|utility",
  "priority": "high|medium|low",
  "reason": "explanation of why modification is needed",
  "suggested_changes": [
    {{
      "type": "add_function|modify_function|add_import|modify_variable",
      "target": "function/class/variable name",
      "description": "detailed description of change"
    }}
  ],
  "cross_file_dependencies": [
    {{
      "source_file": "data_loader.py",
      "target_file": "pipeline.py",
      "linked_element": "load_data",
      "type": "function_usage",
      "reason": "Function load_data used in pipeline.py"
    }}
  ]
}}

Strictly return only the above JSON format with no extra content.
"""
        
        try:
            logger.info(f"🤖 Analyzing file relevance for: {file_path.name} (specifically mentioned: {is_specifically_mentioned})")
            
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )
            
            cleaned = self._clean_json_response(response)
            
            try:
                result = FileAnalysisResult.model_validate_json(cleaned)
                logger.info(f"📊 Analysis result for {file_path.name}: needs_modification={result.needs_modification}, priority={result.priority}")
                return result
            except ValidationError as ve:
                logger.warning(f"[⚠️ VALIDATION ERROR] for {file_path.name}: {ve}")
                logger.warning(f"Raw response: {response}")
                logger.warning(f"Cleaned response: {cleaned}")
                
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for {file_path.name}: {e}")
        
        return self._default_analysis()
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from LLM response."""
        # Remove markdown code blocks
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            response = matches[0].strip()
        else:
            # Find JSON object boundaries
            json_start = response.find("{")
            if json_start != -1:
                response = response[json_start:]
                # Find the last closing brace
                json_end = response.rfind("}")
                if json_end != -1:
                    response = response[:json_end + 1]
        
        # Clean up common issues
        response = response.replace("True", "true").replace("False", "false")
        response = re.sub(r",\s*([}\]])", r"\1", response)  # Remove trailing commas
        response = response.strip()
        
        return response
    
    def _default_analysis(self) -> FileAnalysisResult:
        """Return default analysis when LLM analysis fails."""
        return FileAnalysisResult(
            needs_modification=False,
            modification_type="",
            priority="low",
            reason="No modification needed or analysis failed",
            suggested_changes=[],
            cross_file_dependencies=[]
        )