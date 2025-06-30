import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from utils.llm_client import llm_client
from utils.file_handler import FileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class CodeGeneratorAgent:
    def __init__(self):
        self.system_prompt = """You are a Code Generator Agent. Your job is to generate and modify Python code based on detailed suggestions and requirements.

You should:
1. Generate clean, well-documented Python code
2. Follow Python best practices and PEP 8 standards
3. Include proper error handling
4. Add appropriate comments and docstrings
5. Ensure code is modular and maintainable

Always generate production-ready code that is secure and efficient."""

    async def generate_code_modifications(self, modification_plan: Dict[str, Any]) -> Dict[str, Any]:
        results = {
            "modified_files": [],
            "new_files": [],
            "errors": [],
            "warnings": []
        }

        for file_info in modification_plan.get("files_to_modify", []):
            try:
                file_path = Path(file_info["file_path"])
                suggestions = file_info.get("suggestions", {})

                current_content = FileHandler.read_file(file_path)
                if not current_content:
                    logger.warning(f"Empty or unreadable file: {file_path}")
                    results["errors"].append(f"Could not read file: {file_path}")
                    continue

                modified_content = await self._apply_modifications(current_content, suggestions)
                if modified_content:
                    results["modified_files"].append({
                        "file_path": str(file_path),
                        "original_content": current_content,
                        "modified_content": modified_content,
                        "modifications_applied": len(suggestions.get("modifications", []))
                    })
                else:
                    results["errors"].append(f"Failed to generate modifications for: {file_path}")
            except Exception as e:
                logger.exception(f"Error processing file {file_info.get('file_path')}")
                results["errors"].append(f"Error processing {file_info.get('file_path')}: {str(e)}")

        return results

    async def _apply_modifications(self, current_content: str, suggestions: Dict[str, Any]) -> Optional[str]:
        modifications = suggestions.get("modifications", [])
        if not modifications:
            logger.info("No modifications provided.")
            return current_content

        prompt = f"""
Apply the following modifications to this Python code:

Current Code:
{current_content}

Modifications to Apply:
{json.dumps(modifications, indent=2)}

Rules:
1. Apply ALL modifications in the correct order
2. Maintain existing code structure and formatting
3. Add proper imports if needed
4. Include error handling
5. Add docstrings for new functions/classes
6. Follow PEP 8 standards
7. Preserve existing functionality unless explicitly modified

Return the complete modified code file:
"""

        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            if response:
                return self._extract_code_from_response(response)
            return None
        except Exception as e:
            logger.exception("LLM modification generation failed.")
            return None

    async def generate_new_file(self, file_spec: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        prompt = f"""
Generate a new Python file based on these specifications:

File Specifications:
{json.dumps(file_spec, indent=2)}

Configuration Context:
{json.dumps(config, indent=2)}

Requirements:
1. Create a complete, functional Python file
2. Include all necessary imports
3. Add comprehensive docstrings
4. Include proper error handling
5. Follow Python best practices
6. Make it production-ready

Generate the complete Python file:
"""
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            if response:
                return self._extract_code_from_response(response)
            return None
        except Exception as e:
            logger.exception("Failed to generate new file.")
            return None

    def _extract_code_from_response(self, response: str) -> str:
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()

        lines = response.split('\n')
        code_lines = []
        in_code = False
        for line in lines:
            if not in_code and (line.strip().startswith(('import ', 'from ', 'def ', 'class ', '#')) or 
                                line.strip() == '' or line.startswith('    ')):
                in_code = True
            if in_code:
                code_lines.append(line)
        return '\n'.join(code_lines).strip()

    def validate_generated_code(self, code: str) -> Tuple[bool, List[str]]:
        issues = []

        is_valid, syntax_error = FileHandler.validate_python_syntax(code)
        if not is_valid:
            issues.append(f"Syntax error: {syntax_error}")

        if 'import' not in code and 'def ' in code:
            issues.append("Warning: No imports found, might need dependencies")

        if 'def ' in code and '"""' not in code and "'''" not in code:
            issues.append("Warning: Functions without docstrings detected")

        if 'try:' in code and 'except:' in code and 'except Exception:' not in code:
            issues.append("Warning: Bare except clauses detected")

        return len(issues) == 0 or all(i.startswith("Warning") for i in issues), issues
