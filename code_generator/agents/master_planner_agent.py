import json
import re
import logging
from typing import List, Dict, Any
from pathlib import Path
from utils.file_handler import FileHandler
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MasterPlannerAgent:
    def __init__(self):
        self.system_prompt = """You are a Code Identifier Agent. Your job is to analyze existing code files and identify what changes are needed based on configuration metadata and the developer's request."""

    async def identify_target_files(
        self,
        parsed_config: Dict[str, Any],
        project_path: Path,
        user_question: str
    ) -> List[Dict[str, Any]]:
        logger.info("🔍 Starting file identification process...")

        if not parsed_config or not isinstance(parsed_config, dict):
            logger.error("❌ Invalid parsed_config input.")
            return []

        if not isinstance(project_path, Path) or not project_path.exists():
            logger.error("❌ Invalid or non-existent project_path.")
            return []

        if not user_question or not isinstance(user_question, str):
            logger.error("❌ Invalid user question input.")
            return []

        target_files = []

        try:
            python_files = FileHandler.find_files(project_path, ['.py'])

            for file_path in python_files:
                try:
                    file_info = FileHandler.get_file_info(file_path)
                    file_structure = FileHandler.parse_python_file(file_path)
                    file_content = FileHandler.read_file(file_path)

                    if file_structure and isinstance(file_content, str):
                        analysis = await self._analyze_file_relevance(
                            file_path,
                            file_content,
                            file_structure,
                            parsed_config,
                            user_question
                        )

                        if analysis.get("needs_modification"):
                            target_files.append({
                                "file_path": str(file_path),
                                "file_info": file_info,
                                "structure": file_structure,
                                "analysis": analysis,
                                "priority": analysis.get("priority", "medium")
                            })
                except Exception as fe:
                    logger.warning(f"[⚠️ FILE ERROR] Failed to process {file_path}: {fe}")

            # Prioritize files
            priority_order = {"high": 3, "medium": 2, "low": 1}
            target_files.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)

        except Exception as e:
            logger.exception(f"❌ Unexpected error during file identification: {e}")

        return target_files

    async def _analyze_file_relevance(
        self,
        file_path: Path,
        content: str,
        structure: Dict[str, Any],
        config: Dict[str, Any],
        user_question: str
    ) -> Dict[str, Any]:
        if not all([file_path, content, structure, config, user_question]):
            logger.error("❌ Invalid inputs to _analyze_file_relevance.")
            return self._default_analysis()

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

Pease do not add any extra information in output make it in proper json no comments or any extra info be accurate with the output format.
"""
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if not response or len(response.strip()) < 10:
                logger.warning(f"[LLM] Empty or too short response for file: {file_path}")
                return self._default_analysis()

            cleaned = self._clean_json_response(response)

            if not cleaned.strip().startswith("{"):
                logger.warning(f"[LLM] Non-JSON response for {file_path.name}. Raw output: {response[:200]}")
                return self._default_analysis()

            return json.loads(cleaned)

        except json.JSONDecodeError as jde:
            logger.warning(
                f"⚠️ JSON decode error for file {file_path.name}: {jde}. Raw response:\n{response[:300]}"
            )
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for {file_path.name}: {e}")

        return self._default_analysis()

    def _clean_json_response(self, response: str) -> str:
        """Extract and clean JSON content from LLM response, even if wrapped in extra text."""
        # Step 1: Extract JSON block if wrapped in triple backticks
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            response = matches[0].strip()
        else:
            # Step 2: Try to extract the first curly-brace JSON object manually
            json_start = response.find("{")
            if json_start != -1:
                response = response[json_start:]

        # Step 3: Normalize booleans and remove trailing commas
        response = response.replace("True", "true").replace("False", "false")
        response = re.sub(r",\s*([}\]])", r"\1", response)

        return response.strip()


    def _default_analysis(self) -> Dict[str, Any]:
        """Fallback structure when LLM fails or returns invalid data."""
        return {
            "needs_modification": False,
            "modification_type": "",
            "priority": "low",
            "reason": "No modification needed or analysis failed",
            "suggested_changes": []
        }
