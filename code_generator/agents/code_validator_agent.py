import json
import ast
import re,os
from datetime import datetime
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from utils.llm_client import llm_client
from utils.file_handler import FileHandler

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

    def validate_code_changes(self, modified_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate all code changes and provide comprehensive feedback"""
        
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
            
            # Validate individual file
            file_validation = self._validate_single_file(file_path, modified_content)
            validation_results["files_validated"].append(file_validation)
            
            # Collect errors and warnings
            if file_validation["errors"]:
                validation_results["errors_found"].extend(file_validation["errors"])
                validation_results["overall_status"] = "failed"
            
            if file_validation["warnings"]:
                validation_results["warnings"].extend(file_validation["warnings"])
            
            if file_validation["suggestions"]:
                validation_results["suggestions"].extend(file_validation["suggestions"])
            
            # Auto-fix issues if possible
            if file_validation["errors"] or file_validation["warnings"]:
                fixed_code = self._auto_fix_issues(modified_content, file_validation)
                if fixed_code and fixed_code != modified_content:
                    validation_results["fixed_files"].append({
                        "file_path": file_path,
                        "original_content": modified_content,
                        "fixed_content": fixed_code,
                        "fixes_applied": file_validation["errors"] + file_validation["warnings"]
                    })
        
        return validation_results
    
    def _validate_single_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Validate a single file comprehensively"""
        
        validation = {
            "file_path": file_path,
            "syntax_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "metrics": {}
        }
        
        # Syntax validation
        is_valid, syntax_error = FileHandler.validate_python_syntax(content)
        if not is_valid:
            validation["syntax_valid"] = False
            validation["errors"].append(f"Syntax Error: {syntax_error}")
        
        # Static analysis
        if is_valid:
            static_issues = self._perform_static_analysis(content)
            validation["errors"].extend(static_issues["errors"])
            validation["warnings"].extend(static_issues["warnings"])
            validation["suggestions"].extend(static_issues["suggestions"])
        
        # Code quality metrics
        validation["metrics"] = self._calculate_code_metrics(content)
        
        # Security analysis
        security_issues = self._check_security_issues(content)
        validation["warnings"].extend(security_issues)
        
        # Performance analysis
        performance_suggestions = self._analyze_performance(content)
        validation["suggestions"].extend(performance_suggestions)
        
        return validation
    
    def _perform_static_analysis(self, content: str) -> Dict[str, List[str]]:
        """Perform static analysis on Python code"""
        
        issues = {
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            tree = ast.parse(content)
            
            # Analyze AST for common issues
            for node in ast.walk(tree):
                # Check for bare except clauses
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues["warnings"].append(f"Line {node.lineno}: Bare except clause detected")
                
                # Check for unused variables (simple check)
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.startswith('_') and not target.id.startswith('__'):
                            issues["suggestions"].append(f"Line {node.lineno}: Variable {target.id} appears to be unused")
                
                # Check for long functions
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            issues["suggestions"].append(f"Line {node.lineno}: Function '{node.name}' is very long ({func_length} lines)")
                
                # Check for missing docstrings
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not (node.body and isinstance(node.body[0], ast.Expr) and 
                           isinstance(node.body[0].value, ast.Constant) and 
                           isinstance(node.body[0].value.value, str)):
                        issues["warnings"].append(f"Line {node.lineno}: {node.__class__.__name__} '{node.name}' missing docstring")
        
        except Exception as e:
            issues["errors"].append(f"Static analysis error: {str(e)}")
        
        return issues
    
    def _calculate_code_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate various code quality metrics"""
        
        metrics = {
            "lines_of_code": len(content.split('\n')),
            "blank_lines": len([line for line in content.split('\n') if not line.strip()]),
            "comment_lines": len([line for line in content.split('\n') if line.strip().startswith('#')]),
            "functions_count": content.count('def '),
            "classes_count": content.count('class '),
            "imports_count": content.count('import ') + content.count('from '),
            "complexity_estimate": "low"
        }
        
        # Estimate complexity based on control structures
        complexity_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except:', 'with ']
        complexity_score = sum(content.count(keyword) for keyword in complexity_keywords)
        
        if complexity_score > 20:
            metrics["complexity_estimate"] = "high"
        elif complexity_score > 10:
            metrics["complexity_estimate"] = "medium"
        
        return metrics
    
    def _check_security_issues(self, content: str) -> List[str]:
        """Check for common security issues"""
        
        security_issues = []
        
        # Check for dangerous functions
        dangerous_patterns = [
            (r'eval\s*\(', "Use of eval() function detected - potential security risk"),
            (r'exec\s*\(', "Use of exec() function detected - potential security risk"),
            (r'input\s*\(', "Use of input() function - ensure input validation"),
            (r'subprocess\.(call|run|Popen)', "Use of subprocess - ensure command injection prevention"),
            (r'os\.system\s*\(', "Use of os.system() - potential command injection risk"),
            (r'pickle\.loads?\s*\(', "Use of pickle - potential code execution risk with untrusted data"),
            (r'__import__\s*\(', "Dynamic import detected - ensure input validation")
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, content):
                security_issues.append(f"Security Warning: {message}")
        
        # Check for hardcoded secrets (simple patterns)
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Potential hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Potential hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Potential hardcoded secret")
        ]
        
        for pattern, message in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                security_issues.append(f"Security Warning: {message}")
        
        return security_issues
    
    def _analyze_performance(self, content: str) -> List[str]:
        """Analyze code for performance issues"""
        
        performance_suggestions = []
        
        # Check for inefficient patterns
        if re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', content):
            performance_suggestions.append("Consider using enumerate() instead of range(len())")
        
        if '+=' in content and 'str' in content:
            performance_suggestions.append("Consider using join() for string concatenation in loops")
        
        if re.search(r'\.append\s*\([^)]*for\s+', content):
            performance_suggestions.append("Consider using list comprehension instead of append in loop")
        
        if 'global ' in content:
            performance_suggestions.append("Global variables detected - consider refactoring for better performance")
        
        return performance_suggestions
    
    def _auto_fix_issues(self, content: str, validation_result: Dict[str, Any]) -> Optional[str]:
        """Attempt to automatically fix common issues"""
        
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
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                fixed_code = self._extract_code_from_response(response)
                
                # Validate the fix
                is_valid, _ = FileHandler.validate_python_syntax(fixed_code)
                if is_valid:
                    return fixed_code
            
            return None
            
        except Exception as e:
            print(f"Error auto-fixing issues: {e}")
            return None
    
    def format_code(self, content: str) -> str:
        """Format code according to PEP 8 standards"""
        
        prompt = f"""
Format this Python code according to PEP 8 standards:

Code:
{content}

Rules:
1. Fix indentation (4 spaces)
2. Limit lines to 79 characters where possible
3. Add proper spacing around operators
4. Fix import organization
5. Remove trailing whitespace
6. Maintain functionality

Return the formatted code:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                formatted_code = self._extract_code_from_response(response)
                
                # Validate formatting didn't break syntax
                is_valid, _ = FileHandler.validate_python_syntax(formatted_code)
                if is_valid:
                    return formatted_code
            
            return content  # Return original if formatting fails
            
        except Exception as e:
            print(f"Error formatting code: {e}")
            return content
    
    def add_documentation(self, content: str) -> str:
        """Add comprehensive documentation to code"""
        
        prompt = f"""
Add comprehensive documentation to this Python code:

Code:
{content}

Requirements:
1. Add docstrings to all functions and classes
2. Add inline comments for complex logic
3. Include type hints where appropriate
4. Add module-level docstring
5. Document parameters and return values
6. Maintain code functionality

Return the documented code:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                documented_code = self._extract_code_from_response(response)
                
                # Validate documentation didn't break syntax
                is_valid, _ = FileHandler.validate_python_syntax(documented_code)
                if is_valid:
                    return documented_code
            
            return content
            
        except Exception as e:
            print(f"Error adding documentation: {e}")
            return content
    
    def run_code_quality_checks(self, file_path: Path) -> Dict[str, Any]:
        """Run external code quality tools if available"""
        
        results = {
            "tools_run": [],
            "issues_found": [],
            "suggestions": []
        }
        
        # Try to run flake8 if available
        try:
            result = subprocess.run(['flake8', str(file_path)], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                results["tools_run"].append("flake8")
            else:
                results["issues_found"].extend(result.stdout.split('\n'))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try to run pylint if available
        try:
            result = subprocess.run(['pylint', str(file_path)], 
                                  capture_output=True, text=True, timeout=30)
            results["tools_run"].append("pylint")
            # Parse pylint output (simplified)
            if result.stdout:
                results["suggestions"].extend(result.stdout.split('\n')[:10])  # First 10 lines
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return results
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract clean Python code from LLM response"""
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        return response.strip()
    
    def save_successful_validation_output(self, results: Dict[str, Any], modified_files: List[Dict[str, Any]], output_dir: str = "output/generated_code") -> None:
        """Save validated files, backups, metadata, and logs after successful validation"""

        os.makedirs(os.path.join(output_dir, "modified_files"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "backups"), exist_ok=True)

        # Save modified files and create backups
        for file_info in modified_files:
            file_path = file_info["file_path"]
            modified_content = file_info["modified_content"]
            filename = os.path.basename(file_path)

            # Save modified file
            with open(os.path.join(output_dir, "modified_files", filename), "w", encoding="utf-8") as f:
                f.write(modified_content)

            # Backup original (if exists)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(os.path.join(output_dir, "backups", filename + ".backup"), "w", encoding="utf-8") as f:
                    f.write(original)

        # Save validation report
        with open(os.path.join(output_dir, "validation_report.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Save workflow metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "files": [file["file_path"] for file in modified_files],
            "status": results["overall_status"]
        }
        with open(os.path.join(output_dir, "workflow_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Optional: Execution log
        with open(os.path.join(output_dir, "execution_log.txt"), "w", encoding="utf-8") as f:
            f.write("Validation passed. All files processed successfully.\n")
            for file in modified_files:
                f.write(f"Processed: {file['file_path']}\n")