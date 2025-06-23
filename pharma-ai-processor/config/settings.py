import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class LMStudioConfig:
    """LM Studio configuration"""
    base_url: str = "http://localhost:1234"
    api_key: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0
    
@dataclass
class OCRConfig:
    """OCR processing configuration"""
    model_name: str = "llava"  # Default VLM model for OCR
    max_image_size: int = 2048  # Max image dimension in pixels
    supported_formats: List[str] = field(default_factory=lambda: ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.pdf'])
    dpi: int = 300  # DPI for PDF conversion
    enhance_contrast: bool = True
    remove_noise: bool = True

@dataclass
class ExtractionConfig:
    """Information extraction configuration"""
    model_name: str = "llama-3.1-8b-instruct"
    temperature: float = 0.1
    max_tokens: int = 2000
    extraction_fields: List[str] = field(default_factory=lambda: [
        'patient_name', 'patient_age', 'patient_gender', 'doctor_name',
        'clinic_name', 'prescription_date', 'medications', 'dosages',
        'frequencies', 'durations', 'instructions', 'diagnosis'
    ])

@dataclass
class StructuringConfig:
    """Data structuring configuration"""
    output_format: str = "structured_json"
    validate_data: bool = True
    required_fields: List[str] = field(default_factory=lambda: [
        'patient_name', 'medications'
    ])
    
@dataclass
class CodingConfig:
    """Clinical coding configuration"""
    model_name: str = "llama-3.1-8b-instruct"
    temperature: float = 0.0  # More deterministic for coding
    max_tokens: int = 1000
    coding_systems: List[str] = field(default_factory=lambda: [
        'ICD-10', 'RxNorm', 'SNOMED-CT'
    ])
    enable_drug_coding: bool = True
    enable_diagnosis_coding: bool = True

@dataclass
class ExcelConfig:
    """Excel generation configuration"""
    template_path: Optional[str] = None
    include_metadata: bool = True
    add_timestamp: bool = True
    sheet_names: Dict[str, str] = field(default_factory=lambda: {
        'prescriptions': 'Prescription_Data',
        'medications': 'Medications',
        'coding': 'Clinical_Codes',
        'metadata': 'Processing_Info'
    })

@dataclass
class ProcessingConfig:
    """General processing configuration"""
    batch_size: int = 10
    parallel_processing: bool = False
    max_workers: int = 4
    log_level: str = "INFO"
    save_intermediate: bool = True
    output_directory: str = "data/output"
    backup_enabled: bool = False

@dataclass
class Settings:
    """Main settings class"""
    # Core configurations
    lm_studio: LMStudioConfig = field(default_factory=LMStudioConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    structuring: StructuringConfig = field(default_factory=StructuringConfig)
    coding: CodingConfig = field(default_factory=CodingConfig)
    excel: ExcelConfig = field(default_factory=ExcelConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    # File paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    config_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    
    # Clinical codes file path
    clinical_codes_path: Path = field(default_factory=lambda: Path(__file__).parent / "clinical_codes.json")
    
    def __post_init__(self):
        """Post initialization setup"""
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "input").mkdir(exist_ok=True)
        (self.data_dir / "output").mkdir(exist_ok=True)
        
        # Load environment variables if available
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # LM Studio config
        if os.getenv("LM_STUDIO_URL"):
            self.lm_studio.base_url = os.getenv("LM_STUDIO_URL")
        if os.getenv("LM_STUDIO_API_KEY"):
            self.lm_studio.api_key = os.getenv("LM_STUDIO_API_KEY")
        
        # OCR config
        if os.getenv("OCR_MODEL"):
            self.ocr.model_name = os.getenv("OCR_MODEL")
        
        # Extraction config
        if os.getenv("EXTRACTION_MODEL"):
            self.extraction.model_name = os.getenv("EXTRACTION_MODEL")
        
        # Coding config
        if os.getenv("CODING_MODEL"):
            self.coding.model_name = os.getenv("CODING_MODEL")
        
        # Processing config
        if os.getenv("OUTPUT_DIR"):
            self.processing.output_directory = os.getenv("OUTPUT_DIR")
        if os.getenv("LOG_LEVEL"):
            self.processing.log_level = os.getenv("LOG_LEVEL")
    
    def load_clinical_codes(self) -> Dict:
        """Load clinical codes from JSON file"""
        try:
            with open(self.clinical_codes_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Clinical codes file not found at {self.clinical_codes_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in clinical codes file: {e}")
            return {}
    
    def save_config(self, filepath: Optional[str] = None):
        """Save current configuration to JSON file"""
        if filepath is None:
            filepath = self.config_dir / "current_settings.json"
        
        config_dict = {
            'lm_studio': {
                'base_url': self.lm_studio.base_url,
                'timeout': self.lm_studio.timeout,
                'max_retries': self.lm_studio.max_retries,
                'retry_delay': self.lm_studio.retry_delay
            },
            'ocr': {
                'model_name': self.ocr.model_name,
                'max_image_size': self.ocr.max_image_size,
                'supported_formats': self.ocr.supported_formats,
                'dpi': self.ocr.dpi,
                'enhance_contrast': self.ocr.enhance_contrast,
                'remove_noise': self.ocr.remove_noise
            },
            'extraction': {
                'model_name': self.extraction.model_name,
                'temperature': self.extraction.temperature,
                'max_tokens': self.extraction.max_tokens,
                'extraction_fields': self.extraction.extraction_fields
            },
            'structuring': {
                'output_format': self.structuring.output_format,
                'validate_data': self.structuring.validate_data,
                'required_fields': self.structuring.required_fields
            },
            'coding': {
                'model_name': self.coding.model_name,
                'temperature': self.coding.temperature,
                'max_tokens': self.coding.max_tokens,
                'coding_systems': self.coding.coding_systems,
                'enable_drug_coding': self.coding.enable_drug_coding,
                'enable_diagnosis_coding': self.coding.enable_diagnosis_coding
            },
            'excel': {
                'include_metadata': self.excel.include_metadata,
                'add_timestamp': self.excel.add_timestamp,
                'sheet_names': self.excel.sheet_names
            },
            'processing': {
                'batch_size': self.processing.batch_size,
                'parallel_processing': self.processing.parallel_processing,
                'max_workers': self.processing.max_workers,
                'log_level': self.processing.log_level,
                'save_intermediate': self.processing.save_intermediate,
                'output_directory': self.processing.output_directory,
                'backup_enabled': self.processing.backup_enabled
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Configuration saved to {filepath}")

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reset_settings():
    """Reset global settings instance"""
    global _settings
    _settings = None

# Development/Testing configurations
class DevSettings(Settings):
    """Development environment settings"""
    def __init__(self):
        super().__init__()
        self.lm_studio.timeout = 60
        self.processing.log_level = "DEBUG"
        self.processing.save_intermediate = True
        self.processing.backup_enabled = False

class ProdSettings(Settings):
    """Production environment settings"""
    def __init__(self):
        super().__init__()
        self.lm_studio.timeout = 300
        self.lm_studio.max_retries = 5
        self.processing.log_level = "INFO"
        self.processing.save_intermediate = False
        self.processing.backup_enabled = True
        self.processing.parallel_processing = True

def get_settings_for_env(env: str = "dev") -> Settings:
    """Get settings for specific environment"""
    if env.lower() == "dev":
        return DevSettings()
    elif env.lower() in ["prod", "production"]:
        return ProdSettings()
    else:
        return Settings()