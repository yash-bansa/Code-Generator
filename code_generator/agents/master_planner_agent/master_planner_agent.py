import json
import re
import logging
import yaml
from typing import List, Dict
from pathlib import Path
from utils.file_handler import FileHandler
from utils.llm_client import llm_client
from config.agents_io import MasterPlannerInput, MasterPlannerOutput

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MasterPlannerAgent:
    def __init__(self):
        config_path = Path(__file__).parent / "master_planner_config.yaml"
        try:
            with open(config_path , "r") as f:
                config = yaml.safe_load(f)
            self.system_prompt = config["system_prompt"]
        except Exception as e:
            logger.error(f"[master_planner_agent] Failed to load config: {e}")
            self.system_prompt = "You are a master planner agent. (default fallback prompt)"

    async def identify_target_files(
        self,
        request: MasterPlannerInput
    ) -> List[Dict[str, any]]:
        logger.info("Starting file identification process...")

        if not request.parsed_config or not request.project_path.exists() or not request.user_question:
            logger.error("Invalid input to MasterPlannerAgent.")
            return []

        target_files = []

        try:
            python_files = FileHandler.find_files(request.project_path, ['.py'])

            for file_path in python_files:
                try:
                    file_info = FileHandler.get_file_info(file_path)
                    file_structure = FileHandler.parse_python_file(file_path)
                    file_content = FileHandler.read_file(file_path)

                    if file_structure and isinstance(file_content, str):
                        analysis: MasterPlannerOutput = await self._analyze_file_relevance(
                            file_path,
                            file_content,
                            file_structure,
                            request
                        )

                        if analysis.needs_modification:
                            target_files.append({
                                "file_path": str(file_path),
                                "file_info": file_info,
                                "structure": file_structure,
                                "analysis": analysis.dict(),
                                "priority": analysis.priority
                            })
                except Exception as fe:
                    logger.warning(f"File error in {file_path}: {fe}")

            # Prioritize files
            priority_order = {"high": 3, "medium": 2, "low": 1}
            target_files.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)

        except Exception as e:
            logger.exception(f"Unexpected error in file identification: {e}")

        return target_files

    async def _analyze_file_relevance(
        self,
        file_path: Path,
        content: str,
        structure: Dict[str, any],
        request: MasterPlannerInput
    ) -> MasterPlannerOutput:

        prompt = f"""
Analyze this Python file to determine if it needs modification based on the configuration:

File: {file_path.name}
File Structure:
- Functions: {[f['name'] for f in structure.get('functions', [])]}
- Classes: {[c['name'] for c in structure.get('classes', [])]}
- Imports: {structure.get('imports', [])}

Configuration Requirements:
{json.dumps(request.parsed_config, indent=2)}

User Request:
"{request.user_question}"

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

Please do not add any extra information or comments. Return only valid JSON.
"""

        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if not response or len(response.strip()) < 10:
                return self._default_analysis()

            cleaned = self._clean_json_response(response)
            parsed = MasterPlannerOutput.model_validate_json(cleaned)
            return parsed

        except Exception as e:
            logger.warning(f"LLM error on {file_path.name}: {e}")
            return self._default_analysis()

    def _clean_json_response(self, response: str) -> str:
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            response = matches[0].strip()
        else:
            json_start = response.find("{")
            if json_start != -1:
                response = response[json_start:]

        response = response.replace("True", "true").replace("False", "false")
        response = re.sub(r",\s*([}\]])", r"\1", response)
        return response.strip()

    def _default_analysis(self) -> MasterPlannerOutput:
        return MasterPlannerOutput(
            needs_modification=False,
            modification_type="",
            priority="low",
            reason="No modification needed or analysis failed",
            suggested_changes=[]
        )
