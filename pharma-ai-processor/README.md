# Pharma AI Processor

An AI-powered solution for processing clinical prescriptions and medical bills using agentic AI architecture. This system extracts information from prescription images, structures the data, applies clinical coding, and exports results to Excel format.

## 🎯 Overview

The Pharma AI Processor uses a multi-agent system built with LangGraph to:
- Extract text from prescription images using Vision Language Models (VLMs)
- Parse and structure medical information
- Apply clinical coding (ICD-10, NDC, etc.)
- Generate structured Excel outputs

## 🏗️ Architecture

```
Clinical Prescription/Bill → OCR Agent → Extraction Agent → Structuring Agent → Coding Agent → Excel Output
```

### Agent Workflow
1. **OCR Agent**: Extracts text from images using VLMs via LM Studio
2. **Extraction Agent**: Identifies and extracts relevant medical information
3. **Structuring Agent**: Converts unstructured data to structured format
4. **Coding Agent**: Applies appropriate clinical codes to line items
5. **Excel Generator**: Creates final structured Excel output

## 📁 Project Structure

```
pharma-ai-processor/
├── README.md
├── requirements.txt
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── clinical_codes.json
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── ocr_agent.py
│   │   ├── extraction_agent.py
│   │   ├── structuring_agent.py
│   │   └── coding_agent.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── lm_studio_client.py
│   │   └── excel_generator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── file_handler.py
│   └── workflows/
│       ├── __init__.py
│       └── processing_workflow.py
├── data/
│   ├── input/
│   └── output/
```

## 🚀 Quick Start

### Prerequisites

1. **LM Studio**: Download and install LM Studio
2. **Vision Language Model**: Load a VLM model in LM Studio (e.g., LLaVA, GPT-4V compatible model)
3. **Python 3.8+**: Ensure Python is installed

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pharma-ai-processor
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up LM Studio:
   - Start LM Studio
   - Load a vision-capable model
   - Ensure the server is running on `http://localhost:1234`

### Configuration

1. Update `config/settings.py` with your preferences
2. Modify `config/clinical_codes.json` with relevant clinical codes
3. Place input images in `data/input/`

## 📖 Usage

### Command Line Interface

#### Process Single File
```bash
python src/main.py --input data/input/prescription.jpg --output data/output
```

#### Batch Processing
```bash
python src/main.py --input data/input --output data/output --batch
```

#### Health Check
```bash
python src/main.py --health-check
```

#### Advanced Options
```bash
python src/main.py \
  --input data/input/prescription.pdf \
  --output data/output \
  --lm-studio-url http://localhost:1234
```

### Programmatic Usage

```python
from src.main import PharmaAIProcessor

# Initialize processor
processor = PharmaAIProcessor()

# Process single file
result = processor.process_single_file(
    "data/input/prescription.jpg", 
    "data/output"
)

# Process batch
results = processor.process_batch("data/input", "data/output")
```

## 🧩 Components

### Agents

- **OCR Agent** (`ocr_agent.py`): Extracts text from images using VLMs
- **Extraction Agent** (`extraction_agent.py`): Identifies medical entities and information
- **Structuring Agent** (`structuring_agent.py`): Converts to structured format
- **Coding Agent** (`coding_agent.py`): Applies clinical codes (ICD-10, NDC, CPT)

### Services

- **LM Studio Client** (`lm_studio_client.py`): Interface to LM Studio API
- **Excel Generator** (`excel_generator.py`): Creates structured Excel outputs

### Workflows

- **Processing Workflow** (`processing_workflow.py`): Orchestrates the entire pipeline using LangGraph

## 📊 Output Format

The system generates Excel files with the following structure:

| Field | Description | Example |
|-------|-------------|---------|
| Document ID | Unique identifier | DOC_20241208_143052 |
| Line Item | Extracted prescription item | Amoxicillin 500mg |
| Quantity | Prescribed quantity | 30 tablets |
| Dosage | Dosage instructions | 1 tablet BID |
| ICD-10 Code | Diagnosis code | J01.9 |
| NDC Code | Drug identifier | 12345-678-90 |
| Price | Cost information | $25.99 |
| Notes | Additional information | Take with food |

## 🔧 Configuration

### LM Studio Settings
- Default URL: `http://localhost:1234`
- Recommended Models: LLaVA-v1.6, Qwen-VL, or similar VLMs
- Memory: Minimum 8GB VRAM recommended

### Clinical Codes
Configure clinical coding systems in `config/clinical_codes.json`:
- ICD-10 diagnosis codes
- NDC (National Drug Code) numbers
- CPT procedure codes
- Custom pharmacy codes

## 🧪 Testing

### Test with Sample Data
```bash
# Place test images in data/input/
python src/main.py --input data/input/sample_prescription.jpg
```

### Health Verification
```bash
python src/main.py --health-check
```

## 🚨 Limitations (POC Version)

- **No Authentication**: No user authentication system
- **Basic Error Handling**: Minimal error recovery mechanisms
- **No Database**: Uses file-based storage only
- **Limited Validation**: Basic input validation
- **No API Endpoints**: CLI-only interface
- **Single Threading**: No parallel processing

## 🔮 Future Enhancements

- [ ] Web API with FastAPI
- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] User authentication and authorization
- [ ] Advanced error handling and retry mechanisms
- [ ] Parallel processing for batch operations
- [ ] Real-time processing pipeline
- [ ] Advanced clinical code validation
- [ ] Integration with pharmacy systems
- [ ] Audit logging and compliance features

## 🤝 Contributing

This is a proof-of-concept project. For production deployment:
1. Implement proper error handling
2. Add comprehensive testing
3. Set up CI/CD pipeline
4. Add security measures
5. Implement database layer

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the health status: `python src/main.py --health-check`
2. Verify LM Studio is running with a loaded VLM
3. Ensure input files are in supported formats (JPG, PNG, PDF)
4. Check logs in the output directory
