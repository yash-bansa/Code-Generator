import json
import ast
import re
import os
import logging
import asyncio
from datetime import datetime
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from utils.llm_client import llm_client
from utils.file_handler import FileHandler
import aiofiles
import aiofiles.os


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CodeValidatorAgent:
    def __init__(self):
        self.system_prompt = """You are a Code Validator Agent. Your job is to validate, review, and fix Python code to ensure it meets quality standards.

You should:
1. Check for syntax errors and fix them
2. Validate code logic and functionality
3. Ensure code follows Python best practices
4. Check for security vulnerabilities
5. Optimize performance where possible
6. Fix formatting and style issues

Always provide working, clean, and secure code."""

    async def validate_code_changes(self, modified_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        validation_results = {
            "overall_status": "passed",
            "files_validated": [],
            "errors_found": [],
            "warnings": [],
            "suggestions": [],
            "fixed_files": []
        }

        for file_info in modified_files:
            file_path = file_info["file_path"]
            modified_content = file_info["modified_content"]

            try:
                file_validation = await self._validate_single_file(file_path, modified_content)
                validation_results["files_validated"].append(file_validation)

                if file_validation["errors"]:
                    validation_results["errors_found"].extend(file_validation["errors"])
                    validation_results["overall_status"] = "failed"

                validation_results["warnings"].extend(file_validation["warnings"])
                validation_results["suggestions"].extend(file_validation["suggestions"])

                if file_validation["errors"] or file_validation["warnings"]:
                    fixed_code = await self._auto_fix_issues(modified_content, file_validation)
                    if fixed_code and fixed_code != modified_content:
                        validation_results["fixed_files"].append({
                            "file_path": file_path,
                            "original_content": modified_content,
                            "fixed_content": fixed_code,
                            "fixes_applied": file_validation["errors"] + file_validation["warnings"]
                        })

            except Exception as e:
                logger.error(f"Validation failed for {file_path}: {e}")
                validation_results["errors_found"].append(f"{file_path}: {str(e)}")
                validation_results["overall_status"] = "failed"

        return validation_results

    async def _validate_single_file(self, file_path: str, content: str) -> Dict[str, Any]:
        validation = {
            "file_path": file_path,
            "syntax_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "metrics": {}
        }

        is_valid, syntax_error = FileHandler.validate_python_syntax(content)
        if not is_valid:
            validation["syntax_valid"] = False
            validation["errors"].append(f"Syntax Error: {syntax_error}")
        else:
            try:
                static_issues = self._perform_static_analysis(content)
                validation["errors"].extend(static_issues["errors"])
                validation["warnings"].extend(static_issues["warnings"])
                validation["suggestions"].extend(static_issues["suggestions"])
                validation["metrics"] = self._calculate_code_metrics(content)
                validation["warnings"].extend(self._check_security_issues(content))
                validation["suggestions"].extend(self._analyze_performance(content))
            except Exception as e:
                validation["errors"].append(f"Static analysis failed: {e}")

        return validation

    def _perform_static_analysis(self, content: str) -> Dict[str, List[str]]:
        issues = {"errors": [], "warnings": [], "suggestions": []}
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues["warnings"].append(f"Line {node.lineno}: Bare except clause detected")
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.startswith('_') and not target.id.startswith('__'):
                            issues["suggestions"].append(f"Line {node.lineno}: Variable {target.id} appears unused")
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, 'end_lineno'):
                        length = node.end_lineno - node.lineno
                        if length > 50:
                            issues["suggestions"].append(f"Line {node.lineno}: Function '{node.name}' is very long ({length} lines)")
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not (node.body and isinstance(node.body[0], ast.Expr) and 
                            isinstance(node.body[0].value, ast.Constant) and 
                            isinstance(node.body[0].value.value, str)):
                        issues["warnings"].append(f"Line {node.lineno}: {node.__class__.__name__} '{node.name}' missing docstring")
        except Exception as e:
            issues["errors"].append(f"Static analysis error: {e}")
        return issues

    def _calculate_code_metrics(self, content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        complexity_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except:', 'with ']
        score = sum(content.count(k) for k in complexity_keywords)
        return {
            "lines_of_code": len(lines),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "functions_count": content.count('def '),
            "classes_count": content.count('class '),
            "imports_count": content.count('import ') + content.count('from '),
            "complexity_estimate": "high" if score > 20 else "medium" if score > 10 else "low"
        }

    def _check_security_issues(self, content: str) -> List[str]:
        issues = []
        dangerous = [
            (r'eval\s*\(', "Use of eval() detected - security risk"),
            (r'exec\s*\(', "Use of exec() detected - security risk"),
            (r'input\s*\(', "Use of input() - validate inputs"),
            (r'subprocess\.(call|run|Popen)', "Use of subprocess - ensure safe commands"),
            (r'os\.system\s*\(', "Use of os.system() - injection risk"),
            (r'pickle\.loads?\s*\(', "Use of pickle - untrusted input risk"),
            (r'__import__\s*\(', "Dynamic import - validate input")
        ]
        secrets = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret")
        ]
        for pat, msg in dangerous + secrets:
            if re.search(pat, content, re.IGNORECASE):
                issues.append(f"Security Warning: {msg}")
        return issues

    def _analyze_performance(self, content: str) -> List[str]:
        suggestions = []
        if re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', content):
            suggestions.append("Use enumerate() instead of range(len())")
        if '+=' in content and 'str' in content:
            suggestions.append("Use join() for string concatenation in loops")
        if re.search(r'\.append\s*\([^)]*for\s+', content):
            suggestions.append("Use list comprehension instead of appending in loop")
        if 'global ' in content:
            suggestions.append("Avoid global variables for performance and clarity")
        return suggestions

    async def _auto_fix_issues(self, content: str, validation_result: Dict[str, Any]) -> Optional[str]:
        if not validation_result["errors"] and not validation_result["warnings"]:
            return content

        issues_to_fix = validation_result["errors"] + validation_result["warnings"]

        prompt = f"""
Fix the following issues in this Python code:

Code:
{content}

Issues to Fix:
{json.dumps(issues_to_fix, indent=2)}

Rules:
1. Fix all syntax errors
2. Add missing docstrings
3. Improve error handling
4. Fix formatting issues
5. Maintain original functionality
6. Follow Python best practices

Return the fixed code:
"""
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            if response:
                fixed_code = self._extract_code_from_response(response)
                is_valid, _ = FileHandler.validate_python_syntax(fixed_code)
                return fixed_code if is_valid else None
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
        return None

    def _extract_code_from_response(self, response: str) -> str:
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            return response[start:end].strip() if end != -1 else response[start:].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip() if end != -1 else response[start:].strip()
        return response.strip()
    
    async def save_successful_validation_output(
        self,
        results: Dict[str, Any],
        modified_files: List[Dict[str, Any]],
        output_dir: str = "output/generated_code"
    ) -> None:
        """Asynchronously save validated files, backups, and logs."""

        os.makedirs(os.path.join(output_dir, "modified_files"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "backups"), exist_ok=True)

        # Save modified files and backups
        for file_info in modified_files:
            file_path = file_info["file_path"]
            modified_content = file_info["modified_content"]
            filename = os.path.basename(file_path)

            # Write modified file
            async with aiofiles.open(
                os.path.join(output_dir, "modified_files", filename), "w", encoding="utf-8"
            ) as f:
                await f.write(modified_content)

            # Backup original (if exists)
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    original = await f.read()
                async with aiofiles.open(
                    os.path.join(output_dir, "backups", filename + ".backup"), "w", encoding="utf-8"
                ) as f:
                    await f.write(original)

        # Save validation report
        async with aiofiles.open(os.path.join(output_dir, "validation_report.json"), "w", encoding="utf-8") as f:
            await f.write(json.dumps(results, indent=2))

        # Save metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "files": [file["file_path"] for file in modified_files],
            "status": results["overall_status"]
        }
        async with aiofiles.open(os.path.join(output_dir, "workflow_metadata.json"), "w", encoding="utf-8") as f:
            await f.write(json.dumps(metadata, indent=2))

        # Execution log
        async with aiofiles.open(os.path.join(output_dir, "execution_log.txt"), "w", encoding="utf-8") as f:
            await f.write("Validation passed. All files processed successfully.\n")
            for file in modified_files:
                await f.write(f"Processed: {file['file_path']}\n")