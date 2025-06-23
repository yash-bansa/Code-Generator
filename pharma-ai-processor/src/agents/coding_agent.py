from typing import Dict, List, Tuple
import json
from pathlib import Path
from src.schemas import ProcessingState, PrescriptionData, LineItem
from src.services.lm_studio_client import LMStudioClient

class CodingAgent:
    """Agent responsible for assigning clinical codes to medications and procedures"""
    
    def __init__(self, lm_client: LMStudioClient, clinical_codes_path: str = "config/clinical_codes.json"):
        self.lm_client = lm_client
        self.clinical_codes_path = clinical_codes_path
        self.clinical_codes = self._load_clinical_codes()
        
        self.system_prompt = """You are an expert medical coding agent specialized in assigning clinical codes to medications and medical procedures.

        Your task is to assign appropriate clinical codes to each medication/item from the prescription. Use the following code types:
        - NDC (National Drug Code): For medications
        - ICD-10: For diagnoses and conditions
        - CPT: For procedures and services
        - HCPCS: For healthcare services and supplies

        Given a medication name, find the most appropriate clinical code and return ONLY a JSON object with this structure:
        {
            "clinical_code": "code_value",
            "code_type": "NDC/ICD-10/CPT/HCPCS",
            "confidence": 0.8
        }

        If no appropriate code is found, return:
        {
            "clinical_code": null,
            "code_type": null,
            "confidence": 0.0
        }

        Be conservative and only assign codes when you are reasonably confident.
        """
    
    def _load_clinical_codes(self) -> Dict[str, List[Dict]]:
        """Load clinical codes from configuration file"""
        try:
            codes_path = Path(self.clinical_codes_path)
            if codes_path.exists():
                with open(codes_path, 'r') as f:
                    return json.load(f)
            else:
                # Return default codes structure if file doesn't exist
                return {
                    "ndc_codes": [],
                    "icd10_codes": [],
                    "cpt_codes": [],
                    "hcpcs_codes": []
                }
        except Exception as e:
            print(f"Error loading clinical codes: {e}")
            return {}
    
    def assign_codes(self, state: ProcessingState) -> ProcessingState:
        """Assign clinical codes to all line items"""
        try:
            if not state.structured_data:
                state.errors.append("No structured data available for coding")
                return state
            
            # Create a copy of structured data for coding
            coded_data = state.structured_data.model_copy(deep=True)
            
            # Assign codes to each line item
            for i, line_item in enumerate(coded_data.line_items):
                code_info = self._get_clinical_code(line_item.item_name)
                
                if code_info:
                    line_item.clinical_code = code_info.get('clinical_code')
                    line_item.code_type = code_info.get('code_type')
            
            state.coded_data = coded_data
            state.metadata['coding_completed'] = True
            print(f"Clinical coding completed for document {state.document_id}")
            
        except Exception as e:
            error_msg = f"Clinical coding failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"Error in coding agent: {error_msg}")
        
        return state
    
    def _get_clinical_code(self, medication_name: str) -> Dict[str, any]:
        """Get clinical code for a medication using LLM"""
        try:
            # First try rule-based matching
            rule_based_code = self._rule_based_coding(medication_name)
            if rule_based_code:
                return rule_based_code
            
            # Fall back to LLM-based coding
            return self._llm_based_coding(medication_name)
            
        except Exception as e:
            print(f"Error getting clinical code for {medication_name}: {e}")
            return None
    
    def _rule_based_coding(self, medication_name: str) -> Dict[str, any]:
        """Simple rule-based coding using loaded clinical codes"""
        if not self.clinical_codes:
            return None
        
        medication_lower = medication_name.lower()
        
        # Search through NDC codes first (most common for medications)
        for ndc_entry in self.clinical_codes.get('ndc_codes', []):
            if isinstance(ndc_entry, dict):
                name = ndc_entry.get('name', '').lower()
                if name and name in medication_lower:
                    return {
                        'clinical_code': ndc_entry.get('code'),
                        'code_type': 'NDC',
                        'confidence': 0.9
                    }
        
        return None
    
    def _llm_based_coding(self, medication_name: str) -> Dict[str, any]:
        """Use LLM to assign clinical codes"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user", 
                    "content": f"Assign the most appropriate clinical code for this medication: {medication_name}"
                }
            ]
            
            response = self.lm_client.chat_completion(messages)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                return self._parse_coding_response(content)
            
        except Exception as e:
            print(f"LLM coding error for {medication_name}: {e}")
        
        return {'clinical_code': None, 'code_type': None, 'confidence': 0.0}
    
    def _parse_coding_response(self, response_text: str) -> Dict[str, any]:
        """Parse coding response from LLM"""
        try:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except:
            pass
        
        return {'clinical_code': None, 'code_type': None, 'confidence': 0.0}
    
    def get_coding_summary(self, prescription_data: PrescriptionData) -> Dict[str, any]:
        """Get summary of coding results"""
        total_items = len(prescription_data.line_items)
        coded_items = sum(1 for item in prescription_data.line_items if item.clinical_code)
        
        code_types = {}
        for item in prescription_data.line_items:
            if item.code_type:
                code_types[item.code_type] = code_types.get(item.code_type, 0) + 1
        
        return {
            'total_items': total_items,
            'coded_items': coded_items,
            'coding_rate': coded_items / total_items if total_items > 0 else 0,
            'code_types_distribution': code_types
        }
    
    def validate_codes(self, prescription_data: PrescriptionData) -> List[str]:
        """Validate assigned clinical codes"""
        errors = []
        
        for i, item in enumerate(prescription_data.line_items):
            if item.clinical_code and not item.code_type:
                errors.append(f"Line item {i+1}: Has clinical code but missing code type")
            elif item.code_type and not item.clinical_code:
                errors.append(f"Line item {i+1}: Has code type but missing clinical code")
        
        return errors