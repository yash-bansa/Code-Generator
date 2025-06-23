import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from utils.llm_client import llm_client
from utils.file_handler import FileHandler

class ParserAgent:
    def __init__(self):
        self.system_prompt = """You are a Configuration Parser Agent. Your job is to parse configuration files and extract metadata for code generation.

You should:
1. Parse the configuration structure
2. Extract data source configurations
3. Identify transformation requirements
4. Extract target specifications
5. Generate comprehensive metadata for code generation

Always respond with valid JSON format containing parsed metadata."""

    def parse_config(self, config_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse configuration and extract metadata"""
        
        prompt = f"""
Parse the following configuration and extract metadata:

Configuration:
{json.dumps(config_data, indent=2)}

Extract and structure the following information:
1. Data sources (databases, files, APIs)
2. Data transformations required
3. Output specifications
4. Dependencies and requirements
5. Processing parameters

Return a JSON object with the following structure:
{{
    "data_sources": [
        {{
            "name": "source_name",
            "type": "database|file|api",
            "connection_params": {{}},
            "tables_or_files": []
        }}
    ],
    "transformations": [
        {{
            "name": "transformation_name",
            "type": "filter|aggregate|join|custom",
            "parameters": {{}},
            "input_sources": [],
            "output_target": ""
        }}
    ],
    "outputs": [
        {{
            "name": "output_name",
            "type": "file|database|api",
            "format": "csv|json|parquet|sql",
            "location": "",
            "schema": {{}}
        }}
    ],
    "dependencies": [],
    "processing_config": {{
        "batch_size": 1000,
        "parallel_processing": true,
        "error_handling": "continue|stop|retry"
    }},
    "metadata": {{
        "description": "",
        "version": "",
        "created_by": "",
        "last_modified": ""
    }}
}}
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )
            
            if response:
                # Clean and parse the JSON response
                cleaned_response = self._clean_json_response(response)
                return json.loads(cleaned_response)
            
            return None
            
        except Exception as e:
            print(f"Error parsing config: {e}")
            return None
    
    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON"""
        # Remove markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        return response.strip()
    
    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration structure and completeness"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check required sections
        required_sections = ["data_sources", "transformations", "outputs"]
        for section in required_sections:
            if section not in config_data:
                validation_result["errors"].append(f"Missing required section: {section}")
                validation_result["is_valid"] = False
        
        # Validate data sources
        if "data_sources" in config_data:
            for i, source in enumerate(config_data["data_sources"]):
                if "name" not in source:
                    validation_result["errors"].append(f"Data source {i} missing 'name'")
                    validation_result["is_valid"] = False
                if "type" not in source:
                    validation_result["errors"].append(f"Data source {i} missing 'type'")
                    validation_result["is_valid"] = False
        
        # Validate transformations
        if "transformations" in config_data:
            for i, transform in enumerate(config_data["transformations"]):
                if "name" not in transform:
                    validation_result["warnings"].append(f"Transformation {i} missing 'name'")
                if "input_sources" not in transform:
                    validation_result["errors"].append(f"Transformation {i} missing 'input_sources'")
                    validation_result["is_valid"] = False
        
        # Validate outputs
        if "outputs" in config_data:
            for i, output in enumerate(config_data["outputs"]):
                if "name" not in output:
                    validation_result["errors"].append(f"Output {i} missing 'name'")
                    validation_result["is_valid"] = False
                if "type" not in output:
                    validation_result["errors"].append(f"Output {i} missing 'type'")
                    validation_result["is_valid"] = False
        
        return validation_result
    
    def enrich_metadata(self, parsed_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich parsed configuration with additional metadata"""
        
        prompt = f"""
Analyze the parsed configuration and suggest improvements or additional metadata:

Parsed Configuration:
{json.dumps(parsed_config, indent=2)}

Provide suggestions for:
1. Missing dependencies that might be needed
2. Performance optimizations
3. Error handling improvements  
4. Security considerations
5. Best practices recommendations

Return JSON with enrichment suggestions:
{{
    "suggested_dependencies": [],
    "performance_optimizations": [],
    "error_handling_suggestions": [],
    "security_recommendations": [],
    "best_practices": []
}}
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )
            
            if response:
                cleaned_response = self._clean_json_response(response)
                enrichment = json.loads(cleaned_response)
                
                # Merge enrichment with original config
                parsed_config["enrichment"] = enrichment
                return parsed_config
            
            return parsed_config
            
        except Exception as e:
            print(f"Error enriching metadata: {e}")
            return parsed_config
    
    def extract_file_patterns(self, config_data: Dict[str, Any]) -> List[str]:
        """Extract file patterns that need to be modified"""
        patterns = []
        
        # Extract patterns based on data sources and outputs
        if "data_sources" in config_data:
            for source in config_data["data_sources"]:
                if source.get("type") == "file":
                    patterns.append("data_loader.py")
                elif source.get("type") == "database":
                    patterns.append("db_connector.py")
                elif source.get("type") == "api":
                    patterns.append("api_client.py")
        
        if "transformations" in config_data:
            patterns.append("data_transformer.py")
            patterns.append("pipeline.py")
        
        if "outputs" in config_data:
            patterns.append("data_writer.py")
            patterns.append("output_handler.py")
        
        return list(set(patterns))  # Remove duplicates