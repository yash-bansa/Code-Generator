import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from utils.llm_client import llm_client
from utils.file_handler import FileHandler

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

    def generate_code_modifications(self, modification_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code modifications based on the modification plan"""
        
        results = {
            "modified_files": [],
            "new_files": [],
            "errors": [],
            "warnings": []
        }
        
        for file_info in modification_plan["files_to_modify"]:
            try:
                file_path = Path(file_info["file_path"])
                suggestions = file_info["suggestions"]
                
                # Read current file content
                current_content = FileHandler.read_file(file_path)
                if current_content is None:
                    results["errors"].append(f"Could not read file: {file_path}")
                    continue
                
                # Generate modifications
                modified_content = self._apply_modifications(current_content, suggestions)
                
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
                results["errors"].append(f"Error processing {file_info['file_path']}: {str(e)}")
        
        return results
    
    def _apply_modifications(self, current_content: str, suggestions: Dict[str, Any]) -> Optional[str]:
        """Apply modifications to file content"""
        
        modifications = suggestions.get("modifications", [])
        if not modifications:
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
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1  # Lower temperature for more consistent code generation
            )
            
            if response:
                # Clean the response to extract just the code
                modified_code = self._extract_code_from_response(response)
                return modified_code
            
            return None
            
        except Exception as e:
            print(f"Error applying modifications: {e}")
            return None
    
    def generate_new_file(self, file_spec: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        """Generate a completely new file based on specifications"""
        
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
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return None
            
        except Exception as e:
            print(f"Error generating new file: {e}")
            return None
    
    def refactor_function(self, function_name: str, current_code: str, requirements: Dict[str, Any]) -> Optional[str]:
        """Refactor a specific function based on requirements"""
        
        prompt = f"""
Refactor the function '{function_name}' in this code based on the requirements:

Current Code:
{current_code}

Requirements:
{json.dumps(requirements, indent=2)}

Rules:
1. Maintain the function's interface unless explicitly changed
2. Improve error handling
3. Add/update docstring
4. Optimize performance if possible
5. Follow Python best practices
6. Add type hints if not present

Return the refactored function code:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return None
            
        except Exception as e:
            print(f"Error refactoring function {function_name}: {e}")
            return None
    
    def add_new_function(self, function_spec: Dict[str, Any], existing_code: str) -> Optional[str]:
        """Add a new function to existing code"""
        
        prompt = f"""
Add a new function to this existing Python code:

Existing Code:
{existing_code}

New Function Specification:
{json.dumps(function_spec, indent=2)}

Rules:
1. Insert the function in the appropriate location
2. Include comprehensive docstring
3. Add type hints
4. Include error handling
5. Follow the existing code style
6. Add necessary imports at the top

Return the complete updated code:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return None
            
        except Exception as e:
            print(f"Error adding new function: {e}")
            return None
    
    def optimize_imports(self, code: str) -> str:
        """Optimize and organize imports in Python code"""
        
        prompt = f"""
Optimize and organize the imports in this Python code:

Code:
{code}

Rules:
1. Remove unused imports
2. Group imports: standard library, third-party, local
3. Sort imports alphabetically within groups
4. Use absolute imports where appropriate
5. Maintain functionality

Return the code with optimized imports:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return code  # Return original if optimization fails
            
        except Exception as e:
            print(f"Error optimizing imports: {e}")
            return code
    
    def add_error_handling(self, code: str, error_handling_spec: Dict[str, Any]) -> str:
        """Add comprehensive error handling to code"""
        
        prompt = f"""
Add error handling to this Python code based on the specifications:

Code:
{code}

Error Handling Specifications:
{json.dumps(error_handling_spec, indent=2)}

Rules:
1. Add try-catch blocks where appropriate
2. Include logging for errors
3. Provide meaningful error messages
4. Handle specific exception types
5. Add input validation
6. Maintain code readability

Return the code with added error handling:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return code
            
        except Exception as e:
            print(f"Error adding error handling: {e}")
            return code
    
    def generate_configuration_template(self, config_spec: Dict[str, Any]) -> str:
        """Generate a configuration template based on specifications"""
        
        prompt = f"""
Generate a Python configuration template based on these specifications:

Configuration Specifications:
{json.dumps(config_spec, indent=2)}

Requirements:
1. Create a class-based configuration
2. Include default values
3. Add validation methods
4. Include documentation
5. Support environment variable overrides
6. Add type hints

Generate the complete configuration module:
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            if response:
                return self._extract_code_from_response(response)
            
            return ""
            
        except Exception as e:
            print(f"Error generating configuration template: {e}")
            return ""
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract clean Python code from LLM response"""
        # Remove markdown code blocks
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
        
        # Remove any explanatory text that might be before/after code
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Start collecting when we see Python-like syntax
            if not in_code and (line.strip().startswith(('import ', 'from ', 'def ', 'class ', '#')) or 
                               line.strip() == '' or line.startswith('    ')):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip()
    
    def validate_generated_code(self, code: str) -> Tuple[bool, List[str]]:
        """Validate the generated code for syntax and basic issues"""
        
        issues = []
        
        # Check syntax
        is_valid, syntax_error = FileHandler.validate_python_syntax(code)
        if not is_valid:
            issues.append(f"Syntax error: {syntax_error}")
        
        # Check for common issues
        if 'import' not in code and 'def ' in code:
            issues.append("Warning: No imports found, might need dependencies")
        
        if 'def ' in code and '"""' not in code and "'''" not in code:
            issues.append("Warning: Functions without docstrings detected")
        
        if 'try:' in code and 'except:' in code and 'except Exception:' not in code:
            issues.append("Warning: Bare except clauses detected")
        
        return len(issues) == 0 or (len(issues) == len([i for i in issues if i.startswith("Warning")])), issues