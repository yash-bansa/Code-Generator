from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class LineItem(BaseModel):
    """Individual line item from prescription/bill"""
    item_name: str
    quantity: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    clinical_code: Optional[str] = None
    code_type: Optional[str] = None  # ICD-10, NDC, CPT, etc.
    raw_text: Optional[str] = None

class PrescriptionData(BaseModel):
    """Structured prescription/bill data"""
    document_id: str
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_id: Optional[str] = None
    prescription_date: Optional[str] = None
    pharmacy_name: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    total_amount: Optional[float] = None
    raw_text: Optional[str] = None

class ProcessingState(BaseModel):
    """State object for LangGraph workflow"""
    input_file_path: str
    document_id: str
    raw_ocr_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    structured_data: Optional[PrescriptionData] = None
    coded_data: Optional[PrescriptionData] = None
    output_file_path: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ClinicalCode(BaseModel):
    """Clinical code mapping"""
    code: str
    description: str
    code_type: str  # ICD-10, NDC, CPT, etc.
    category: Optional[str] = None