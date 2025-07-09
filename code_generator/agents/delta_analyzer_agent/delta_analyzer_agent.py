import json
import re
import logging
from typing import List, Dict, Any
from pathlib import Path
import yaml
from utils.file_handler import FileHandler
from utils.llm_client import llm_client
from config.agents_io import DeltaAnalyzerInput, DeltaAnalyzerOutput

logger = logging.getLogger(__name__)

class DeltaAnalyzerAgent:
    def __init__(self):
        config_path = Path(__file__).parent / "delta_analyzer_config.yaml"
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            self.system_prompt = config["system_prompt"]
        except Exception as e:
            logger.error(f"[delta_analyzer_agent] Failed to load config: {e}")
            self.system_prompt = "You are a delta analyzer agent. (default fallback prompt)"

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

        # Enhanced input extraction - utilizing all available data
        file_analysis = target_file.get('analysis', {})
        file_structure = target_file.get('structure', {})
        file_info = target_file.get('file_info', {})
        
        input_data = DeltaAnalyzerInput(
            file_path=file_path,
            file_content=file_content,
            file_analysis=file_analysis,
            config=parsed_config
        )

        # Enhanced prompt construction utilizing all available data
        prompt = self._build_comprehensive_prompt(
            input_data, file_structure, file_info, file_analysis
        )

        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )
            if response:
                cleaned_response = self._clean_json_response(response)
                parsed = DeltaAnalyzerOutput.model_validate_json(cleaned_response)
                return {
                    **parsed.dict(),
                    "file_path": file_path,
                    "timestamp": file_info.get('modified', 0),
                    "original_priority": file_analysis.get('priority', 'medium'),
                    "modification_type": file_analysis.get('modification_type', 'general')
                }
        except json.JSONDecodeError as je:
            logger.warning(f"[DeltaAnalyzerAgent] JSON decode error for {file_path}: {je}")
        except Exception as e:
            logger.error(f"[DeltaAnalyzerAgent] Error analyzing file {file_path}: {e}")
        
        return {"modifications": []}

    def _build_comprehensive_prompt(self, input_data: DeltaAnalyzerInput, 
                                  file_structure: Dict[str, Any], 
                                  file_info: Dict[str, Any],
                                  file_analysis: Dict[str, Any]) -> str:
        """Build enhanced prompt utilizing all available data."""
        
        # Extract structure information
        functions_info = file_structure.get('functions', [])
        classes_info = file_structure.get('classes', [])
        imports_info = file_structure.get('imports', [])
        variables_info = file_structure.get('variables', [])
        
        # Extract analysis information
        suggested_changes = file_analysis.get('suggested_changes', [])
        cross_dependencies = file_analysis.get('cross_file_dependencies', [])
        modification_type = file_analysis.get('modification_type', 'general')
        reason = file_analysis.get('reason', '')
        
        prompt = f"""
Generate detailed code modification suggestions for this file:

FILE INFORMATION:
- Path: {input_data.file_path}
- Size: {file_info.get('size', 'unknown')} bytes
- Extension: {file_info.get('extension', 'unknown')}
- Modification Type: {modification_type}
- Priority: {file_analysis.get('priority', 'medium')}

EXISTING CODE STRUCTURE:
- Functions: {json.dumps(functions_info, indent=2)}
- Classes: {json.dumps(classes_info, indent=2)}
- Current Imports: {json.dumps(imports_info, indent=2)}
- Variables: {json.dumps(variables_info, indent=2)}

PRE-ANALYSIS INSIGHTS:
- Modification Reason: {reason}
- Pre-identified Changes: {json.dumps(suggested_changes, indent=2)}

CROSS-FILE DEPENDENCIES:
{json.dumps(cross_dependencies, indent=2)}

CONFIGURATION REQUIREMENTS:
{json.dumps(input_data.config, indent=2)}

CURRENT FILE CONTENT:
{input_data.file_content}

INSTRUCTIONS:
1. Build upon the pre-identified changes and create detailed implementation steps
2. Use the existing code structure information to provide precise line numbers
3. Consider cross-file dependencies when suggesting modifications
4. Ensure compatibility with the identified functions, classes, and variables
5. Leverage the current imports list to suggest minimal additional dependencies
6. Address the specific modification type: {modification_type}

Return ONLY a valid JSON object with detailed code changes following the expected format.
"""
        return prompt

    async def create_modification_plan(self, target_files: List[Dict[str, Any]], parsed_config: Dict[str, Any]) -> Dict[str, Any]:
        plan = {
            "files_to_modify": [],
            "execution_order": [],
            "dependencies": [], 
            "estimated_complexity": "low",
            "risks": [],
            "backup_required": True,
            "cross_file_impact": []  # Enhanced: Track cross-file impacts
        }

        # Enhanced: Collect all cross-file dependencies first
        all_dependencies = self._extract_all_dependencies(target_files)
        
        for target_file in target_files:
            suggestions = await self.suggest_file_changes(target_file, parsed_config)
            
            # Enhanced: Use actual priority from analysis
            file_analysis = target_file.get('analysis', {})
            actual_priority = file_analysis.get('priority', 'medium')
            
            plan["files_to_modify"].append({
                "file_path": target_file['file_path'],
                "priority": actual_priority,  # Use actual priority instead of default
                "modification_type": file_analysis.get('modification_type', 'general'),
                "suggestions": suggestions,
                "cross_dependencies": file_analysis.get('cross_file_dependencies', [])
            })

        # Enhanced execution order considering dependencies and priorities
        plan["execution_order"] = self._determine_enhanced_execution_order(
            plan["files_to_modify"], all_dependencies
        )
        
        # Enhanced complexity calculation
        plan["estimated_complexity"] = self._calculate_enhanced_complexity(plan["files_to_modify"])
        
        # Enhanced risk assessment
        plan["risks"] = self._assess_risks(plan["files_to_modify"], all_dependencies)
        
        # Enhanced dependency tracking
        plan["dependencies"] = all_dependencies
        plan["cross_file_impact"] = self._analyze_cross_file_impact(target_files)

        return plan

    def _extract_all_dependencies(self, target_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and consolidate all cross-file dependencies."""
        all_deps = []
        for target_file in target_files:
            file_deps = target_file.get('analysis', {}).get('cross_file_dependencies', [])
            for dep in file_deps:
                if dep not in all_deps:
                    all_deps.append(dep)
        return all_deps

    def _determine_enhanced_execution_order(self, files_to_modify: List[Dict[str, Any]], 
                                          dependencies: List[Dict[str, Any]]) -> List[str]:
        """Enhanced execution order considering dependencies and priorities."""
        order = []
        
        # Priority-based ordering with dependency consideration
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        
        # Sort by priority first
        sorted_files = sorted(files_to_modify, 
                            key=lambda x: priority_order.get(x.get('priority', 'medium'), 1))
        
        # Apply keyword-based ordering within same priority
        priority_keywords = ['config', 'util', 'load', 'input', 'process', 'transform', 'output', 'write']
        
        for priority in ['high', 'medium', 'low']:
            priority_files = [f for f in sorted_files if f.get('priority') == priority]
            
            # Apply keyword ordering
            for keyword in priority_keywords:
                for file_info in priority_files:
                    file_path = Path(file_info["file_path"])
                    if keyword in file_path.name.lower() and file_info["file_path"] not in order:
                        order.append(file_info["file_path"])
            
            # Add remaining files of this priority
            for file_info in priority_files:
                if file_info["file_path"] not in order:
                    order.append(file_info["file_path"])

        return order

    def _calculate_enhanced_complexity(self, files_to_modify: List[Dict[str, Any]]) -> str:
        """Enhanced complexity calculation considering multiple factors."""
        total_modifications = sum(len(f["suggestions"].get("modifications", [])) for f in files_to_modify)
        high_priority_files = sum(1 for f in files_to_modify if f.get("priority") == "high")
        cross_deps_count = sum(len(f.get("cross_dependencies", [])) for f in files_to_modify)
        
        complexity_score = total_modifications + (high_priority_files * 5) + (cross_deps_count * 2)
        
        if complexity_score > 30:
            return "high"
        elif complexity_score > 15:
            return "medium"
        else:
            return "low"

    def _assess_risks(self, files_to_modify: List[Dict[str, Any]], 
                     dependencies: List[Dict[str, Any]]) -> List[str]:
        """Assess potential risks based on file analysis."""
        risks = []
        
        # Check for high-priority modifications
        high_priority_count = sum(1 for f in files_to_modify if f.get("priority") == "high")
        if high_priority_count > 2:
            risks.append("Multiple high-priority files require modification")
        
        # Check for complex cross-dependencies
        if len(dependencies) > 3:
            risks.append("Complex cross-file dependencies detected")
        
        # Check for core functionality changes
        core_files = ['main', 'config', 'init', 'core']
        for file_info in files_to_modify:
            file_path = Path(file_info["file_path"]).stem.lower()
            if any(core in file_path for core in core_files):
                risks.append(f"Core functionality file modification: {file_info['file_path']}")
        
        return risks

    def _analyze_cross_file_impact(self, target_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze the impact of changes across files."""
        impacts = []
        
        for target_file in target_files:
            file_path = target_file.get('file_path')
            cross_deps = target_file.get('analysis', {}).get('cross_file_dependencies', [])
            
            if cross_deps:
                impacts.append({
                    "source_file": file_path,
                    "affected_files": [dep.get('target_file') for dep in cross_deps],
                    "impact_type": [dep.get('type') for dep in cross_deps],
                    "linked_elements": [dep.get('linked_element') for dep in cross_deps]
                })
        
        return impacts

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