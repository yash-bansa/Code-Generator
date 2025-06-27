# agents/master_planner_agent.py

from typing import List, Dict, Any
from pathlib import Path
from utils.file_handler import FileHandler
from utils.llm_client import llm_client
import json, re

class MasterPlannerAgent:
    def __init__(self):
        self.system_prompt = """You are a Code Identifier Agent. Your job is to analyze existing code files and identify what changes are needed based on configuration metadata..."""

    def identify_target_files(self, parsed_config: Dict[str, Any], project_path: Path, user_question: str) -> List[Dict[str, Any]]:
        python_files = FileHandler.find_files(project_path, ['.py'])
        target_files = []

        for file_path in python_files:
            file_info = FileHandler.get_file_info(file_path)
            file_structure = FileHandler.parse_python_file(file_path)
            file_content = FileHandler.read_file(file_path)

            print(f"[DEBUG] File: {file_path.name}, Content Type: {type(file_content)}")

            if file_structure and isinstance(file_content, str):
                analysis = self._analyze_file_relevance(
                    file_path, file_content, file_structure, parsed_config, user_question
                )

                if analysis.get('needs_modification'):
                    target_files.append({
                        'file_path': str(file_path),
                        'file_info': file_info,
                        'structure': file_structure,
                        'analysis': analysis,
                        'priority': analysis.get('priority', 'medium')
                    })

        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        target_files.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)

        return target_files

    def _analyze_file_relevance(self, file_path: Path, content: str, structure: Dict, config: Dict[str, Any], user_question: str) -> Dict[str, Any]:
        prompt = f"""
Analyze this Python file to determine if it needs modification based on the configuration:

File: {file_path.name}
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
    ]
}}
"""
        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if response:
                cleaned_response = self._clean_json_response(response)
                # print(f"[DEBUG] LLM Response (cleaned): {cleaned_response[:300]}")
                return json.loads(cleaned_response)

            return {"needs_modification": False}

        except Exception as e:
            print(f"Error analyzing file {file_path}: {e}")
            return {"needs_modification": False}

    def _clean_json_response(self, response: str) -> str:
        """Extract and clean JSON-like content from LLM response."""
        # Step 1: Extract content between triple backticks if present
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        if matches:
            response = matches[0].strip()
        
        # Step 2: Try fixing common JSON errors
        response = response.replace('\n', '')
        response = response.replace("True", "true").replace("False", "false")
        
        # Remove trailing commas (JSON does not support them)
        response = re.sub(r",\s*([}\]])", r"\1", response)

        return response