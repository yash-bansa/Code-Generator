from typing import Dict, Any, List
from src.schemas import ProcessingState, PrescriptionData, LineItem

class StructuringAgent:
    """Agent responsible for converting extracted data into structured Pydantic models"""
    
    def __init__(self):
        pass
    
    def structure_data(self, state: ProcessingState) -> ProcessingState:
        """Convert extracted dictionary data into structured Pydantic models"""
        try:
            if not state.extracted_data:
                state.errors.append("No extracted data available for structuring")
                return state
            
            # Create structured prescription data
            structured_data = self._create_prescription_data(
                state.extracted_data, 
                state.document_id,
                state.raw_ocr_text
            )
            
            state.structured_data = structured_data
            state.metadata['structuring_completed'] = True
            print(f"Data structuring completed for document {state.document_id}")
            
        except Exception as e:
            error_msg = f"Data structuring failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"Error in structuring agent: {error_msg}")
        
        return state
    
    def _create_prescription_data(self, extracted_data: Dict[str, Any], document_id: str, raw_text: str) -> PrescriptionData:
        """Create PrescriptionData object from extracted dictionary"""
        
        # Create line items
        line_items = []
        raw_line_items = extracted_data.get('line_items', [])
        
        for item_data in raw_line_items:
            if isinstance(item_data, dict) and item_data.get('item_name'):
                line_item = LineItem(
                    item_name=self._clean_string(item_data.get('item_name')),
                    quantity=self._clean_string(item_data.get('quantity')),
                    unit_price=self._safe_float(item_data.get('unit_price')),
                    total_price=self._safe_float(item_data.get('total_price')),
                    dosage=self._clean_string(item_data.get('dosage')),
                    frequency=self._clean_string(item_data.get('frequency')),
                    duration=self._clean_string(item_data.get('duration')),
                    raw_text=item_data.get('raw_text', '')
                )
                line_items.append(line_item)
        
        # Create prescription data
        prescription_data = PrescriptionData(
            document_id=document_id,
            patient_name=self._clean_string(extracted_data.get('patient_name')),
            patient_id=self._clean_string(extracted_data.get('patient_id')),
            doctor_name=self._clean_string(extracted_data.get('doctor_name')),
            doctor_id=self._clean_string(extracted_data.get('doctor_id')),
            prescription_date=self._clean_string(extracted_data.get('prescription_date')),
            pharmacy_name=self._clean_string(extracted_data.get('pharmacy_name')),
            line_items=line_items,
            total_amount=self._safe_float(extracted_data.get('total_amount')),
            raw_text=raw_text
        )
        
        return prescription_data
    
    def _clean_string(self, value: Any) -> str:
        """Clean and validate string values"""
        if value is None:
            return None
        
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        
        # Convert other types to string
        return str(value).strip() if str(value).strip() else None
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float"""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            
            if isinstance(value, str):
                # Remove common currency symbols and spaces
                cleaned = value.replace('$', '').replace(',', '').replace(' ', '')
                if cleaned:
                    return float(cleaned)
            
            return None
        except (ValueError, TypeError):
            return None
    
    def validate_structure(self, data: PrescriptionData) -> List[str]:
        """Validate structured data and return list of validation errors"""
        errors = []
        
        if not data.line_items:
            errors.append("No line items found in prescription")
        
        for i, item in enumerate(data.line_items):
            if not item.item_name:
                errors.append(f"Line item {i+1}: Missing item name")
        
        return errors
    
    def get_summary_stats(self, data: PrescriptionData) -> Dict[str, Any]:
        """Get summary statistics for structured data"""
        return {
            'total_line_items': len(data.line_items),
            'items_with_prices': sum(1 for item in data.line_items if item.total_price is not None),
            'items_with_dosage': sum(1 for item in data.line_items if item.dosage is not None),
            'has_patient_info': bool(data.patient_name),
            'has_doctor_info': bool(data.doctor_name),
            'has_total_amount': bool(data.total_amount)
        }