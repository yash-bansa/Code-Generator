# agents/delta_analyzer_agent.py

import json
import re
import logging
from typing import List, Dict, Any
from pathlib import Path

from utils.file_handler import FileHandler
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)


class DeltaAnalyzerAgent:
    def __init__(self):
        self.system_prompt = """You are a Delta Analyzer Agent specializing in precise code modification planning.

ROLE:
Analyze target files and generate detailed, actionable code change plans based on configuration requirements.

ANALYSIS FOCUS:
1. Identify exact code locations requiring changes
2. Generate specific code modifications (add/modify/delete)
3. Determine import dependencies and requirements
4. Suggest testing approaches for changes
5. Identify potential risks and issues

MODIFICATION TYPES:
- add: Insert new code (functions, classes, variables)
- modify: Change existing code with specific replacements
- delete: Remove obsolete or conflicting code

TARGET TYPES:
- function: Function definitions and calls
- class: Class definitions and methods
- import: Import statements and dependencies
- variable: Variable assignments and configurations
- comment: Documentation and comments

RESPONSE REQUIREMENTS:
- Provide line numbers when possible
- Include both old and new code for modifications
- Explain the reasoning for each change
- Suggest comprehensive testing approaches
- Identify potential breaking changes

EXPECTED JSON FORMAT:
{
  "modifications": [
    {
      "action": "add|modify|delete",
      "target_type": "function|class|import|variable|comment",
      "target_name": "name",
      "line_number": 0,
      "old_code": "code before change (if applicable)",
      "new_code": "code after change",
      "explanation": "why this change is required"
    }
  ],
  "new_dependencies": [],
  "testing_suggestions": [],
  "potential_issues": []
}

Return ONLY valid JSON with NO additional text or explanations."""

    async def suggest_file_changes(self, target_file: Dict[str, Any], parsed_config: Dict[str, Any]) -> Dict[str, Any]:
        file_path = target_file.get('file_path')
        if not file_path:
            logger.warning("[DeltaAnalyzerAgent] Missing file_path in target_file")
            return {"modifications": []}

        try:
            file_content = FileHandler.read_file(Path(file_path))
        except Exception as e:
            logger.error(f"[DeltaAnalyzerAgent] Failed to read file {file_path}: {e}")
            return {"modifications": []}

        prompt = f"""
Generate detailed code modification suggestions for this file:

File Path: {file_path}
Current Analysis: {json.dumps(target_file.get('analysis', {}), indent=2)}
Configuration: {json.dumps(parsed_config, indent=2)}

Current File Content:
{file_content}

Return ONLY a valid JSON object with detailed code changes as described in the expected format.
"""

        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if response:
                cleaned_response = self._clean_json_response(response)
                parsed = json.loads(cleaned_response)
                return {
                    **parsed,
                    "file_path": file_path,
                    "timestamp": FileHandler.get_file_info(Path(file_path)).get('modified', 0)
                }

        except json.JSONDecodeError as je:
            logger.warning(f"[DeltaAnalyzerAgent] JSON decode error for {file_path}: {je}")
        except Exception as e:
            logger.error(f"[DeltaAnalyzerAgent] Error analyzing file {file_path}: {e}")

        return {"modifications": []}

    async def create_modification_plan(self, target_files: List[Dict[str, Any]], parsed_config: Dict[str, Any]) -> Dict[str, Any]:
        plan = {
            "files_to_modify": [],
            "execution_order": [],
            "dependencies": [],
            "estimated_complexity": "low",
            "risks": [],
            "backup_required": True
        }

        for target_file in target_files:
            suggestions = await self.suggest_file_changes(target_file, parsed_config)
            plan["files_to_modify"].append({
                "file_path": target_file['file_path'],
                "priority": target_file.get('priority', 'medium'),
                "suggestions": suggestions
            })

        plan["execution_order"] = self._determine_execution_order(plan["files_to_modify"])

        total_modifications = sum(len(f["suggestions"].get("modifications", [])) for f in plan["files_to_modify"])
        if total_modifications > 20:
            plan["estimated_complexity"] = "high"
        elif total_modifications > 10:
            plan["estimated_complexity"] = "medium"

        return plan

    def _determine_execution_order(self, files_to_modify: List[Dict[str, Any]]) -> List[str]:
        order = []
        priority_keywords = ['config', 'util', 'load', 'input', 'process', 'transform', 'output', 'write']

        for keyword in priority_keywords:
            for file_info in files_to_modify:
                file_path = Path(file_info["file_path"])
                if keyword in file_path.name.lower() and file_info["file_path"] not in order:
                    order.append(file_info["file_path"])

        for file_info in files_to_modify:
            if file_info["file_path"] not in order:
                order.append(file_info["file_path"])

        return order

    def _clean_json_response(self, response: str) -> str:
        """Extract and clean JSON-like content from LLM response."""
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, response, re.DOTALL)

        if matches:
            response = matches[0].strip()

        response = response.replace('\n', '')
        response = response.replace("True", "true").replace("False", "false")
        response = re.sub(r",\s*([}\]])", r"\1", response)

        return response.strip()
