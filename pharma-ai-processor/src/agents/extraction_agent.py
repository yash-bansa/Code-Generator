from typing import Dict, Any
import json
import re
from src.services.lm_studio_client import LMStudioClient
from src.schemas import ProcessingState

class ExtractionAgent:
    """Agent responsible for extracting structured information from OCR text"""
    
    def __init__(self, lm_client: LMStudioClient):
        self.lm_client = lm_client
        self.system_prompt = """You are an expert medical data extraction agent specialized in processing prescription and pharmacy bill text.

        Your task is to extract key information from the OCR text and return it as a structured JSON object.

        Extract the following information:
        1. Patient Information:
           - Patient name
           - Patient ID (if available)
        2. Doctor Information:
           - Doctor name
           - Doctor ID/license number (if available)  
        3. Prescription Details:
           - Prescription date
           - Pharmacy name
        4. Line Items (medications/services):
           - Item name (medication name)
           - Quantity
           - Unit price
           - Total price
           - Dosage information
           - Frequency (how often to take)
           - Duration (how long to take)
        5. Financial Information:
           - Total amount

        Return ONLY a valid JSON object with this structure:
        {
            "patient_name": "string or null",
            "patient_id": "string or null", 
            "doctor_name": "string or null",
            "doctor_id": "string or null",
            "prescription_date": "string or null",
            "pharmacy_name": "string or null",
            "line_items": [
                {
                    "item_name": "string",
                    "quantity": "string or null",
                    "unit_price": number or null,
                    "total_price": number or null,
                    "dosage": "string or null",
                    "frequency": "string or null", 
                    "duration": "string or null",
                    "raw_text": "original text for this item"
                }
            ],
            "total_amount": number or null
        }

        If information is not found or unclear, use null values. Be conservative and accurate.
        """
    
    def extract_information(self, state: ProcessingState) -> ProcessingState:
        """Extract structured information from OCR text"""
        try:
            if not state.raw_ocr_text:
                state.errors.append("No OCR text available for extraction")
                return state
            
            messages = [
                {
                    "role": "system", 
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": f"Extract structured information from this prescription/bill text:\n\n{state.raw_ocr_text}"
                }
            ]
            
            response = self.lm_client.chat_completion(messages)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                
                # Try to parse JSON from response
                extracted_data = self._parse_json_from_response(content)
                
                if extracted_data:
                    state.extracted_data = extracted_data
                    state.metadata['extraction_completed'] = True
                    print(f"Information extraction completed for document {state.document_id}")
                else:
                    state.errors.append("Failed to parse extracted information as JSON")
            else:
                state.errors.append("Failed to get extraction response from LLM")
                
        except Exception as e:
            error_msg = f"Information extraction failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"Error in extraction agent: {error_msg}")
        
        return state
    
    def _parse_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling potential formatting issues"""
        try:
            # First try direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON block in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Try to clean up common formatting issues
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {response_text[:200]}...")
                return None
    
    def validate_extracted_data(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data structure"""
        required_keys = ['line_items']
        
        if not all(key in data for key in required_keys):
            return False
        
        if not isinstance(data.get('line_items'), list):
            return False
        
        # Check if we have at least one line item with item_name
        line_items = data.get('line_items', [])
        if not line_items:
            return False
        
        for item in line_items:
            if not isinstance(item, dict) or 'item_name' not in item:
                return False
        
        return True