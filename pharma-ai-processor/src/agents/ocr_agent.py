from typing import Dict, Any
import base64
from pathlib import Path
from src.services.lm_studio_client import LMStudioClient
from src.schemas import ProcessingState

class OCRAgent:
    """Agent responsible for extracting text from prescription images using VLM"""
    
    def __init__(self, lm_client: LMStudioClient):
        self.lm_client = lm_client
        self.system_prompt = """You are an expert OCR agent specialized in reading medical prescriptions and pharmacy bills.
        
        Your task is to:
        1. Carefully read all text in the image
        2. Extract ALL visible text, maintaining structure and layout
        3. Pay special attention to:
           - Patient information
           - Doctor information
           - Medication names and details
           - Quantities, dosages, frequencies
           - Prices and totals
           - Dates
        
        Provide the extracted text in a clear, structured format that preserves the original layout as much as possible.
        """
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for VLM processing"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_text(self, state: ProcessingState) -> ProcessingState:
        """Extract text from prescription image using VLM"""
        try:
            # Check if input file exists
            if not Path(state.input_file_path).exists():
                state.errors.append(f"Input file not found: {state.input_file_path}")
                return state
            
            # Encode image
            image_base64 = self.encode_image(state.input_file_path)
            
            # Prepare VLM request
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract all text from this prescription/medical bill image:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Get OCR result from VLM
            response = self.lm_client.chat_completion(messages)
            
            if response and 'choices' in response:
                extracted_text = response['choices'][0]['message']['content']
                state.raw_ocr_text = extracted_text
                state.metadata['ocr_completed'] = True
                print(f"OCR completed for document {state.document_id}")
            else:
                state.errors.append("Failed to get OCR response from VLM")
                
        except Exception as e:
            error_msg = f"OCR extraction failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"Error in OCR agent: {error_msg}")
        
        return state
    
    def validate_ocr_quality(self, text: str) -> float:
        """Simple OCR quality validation (0-1 score)"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        # Basic heuristics for medical text quality
        medical_keywords = ['patient', 'doctor', 'medication', 'mg', 'ml', 'tablet', 'capsule', 'prescription']
        found_keywords = sum(1 for keyword in medical_keywords if keyword.lower() in text.lower())
        
        return min(found_keywords / len(medical_keywords), 1.0)