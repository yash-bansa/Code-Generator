from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.schemas import ProcessingState
from src.agents.ocr_agent import OCRAgent
from src.agents.extraction_agent import ExtractionAgent
from src.agents.structuring_agent import StructuringAgent
from src.agents.coding_agent import CodingAgent
from src.services.excel_generator import ExcelGenerator
from src.services.lm_studio_client import LMStudioClient

class PharmaProcessingWorkflow:
    """LangGraph workflow for processing pharmaceutical prescriptions"""
    
    def __init__(self, lm_studio_client: LMStudioClient):
        self.lm_client = lm_studio_client
        self.excel_generator = ExcelGenerator()
        
        # Initialize agents
        self.ocr_agent = OCRAgent(self.lm_client)
        self.extraction_agent = ExtractionAgent(self.lm_client)
        self.structuring_agent = StructuringAgent()
        self.coding_agent = CodingAgent(self.lm_client)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the state graph
        workflow = StateGraph(ProcessingState)
        
        # Add nodes for each processing step
        workflow.add_node("ocr", self._ocr_step)
        workflow.add_node("extraction", self._extraction_step)
        workflow.add_node("structuring", self._structuring_step)
        workflow.add_node("coding", self._coding_step)
        workflow.add_node("excel_generation", self._excel_generation_step)
        
        # Define the workflow edges
        workflow.set_entry_point("ocr")
        
        workflow.add_edge("ocr", "extraction")
        workflow.add_edge("extraction", "structuring")
        workflow.add_edge("structuring", "coding")
        workflow.add_edge("coding", "excel_generation")
        workflow.add_edge("excel_generation", END)
        
        return workflow.compile()
    
    def _ocr_step(self, state: ProcessingState) -> ProcessingState:
        """OCR processing step"""
        print(f"Starting OCR for document: {state.document_id}")
        return self.ocr_agent.extract_text(state)
    
    def _extraction_step(self, state: ProcessingState) -> ProcessingState:
        """Information extraction step"""
        print(f"Starting information extraction for document: {state.document_id}")
        
        if state.errors:
            print(f"Skipping extraction due to previous errors: {state.errors}")
            return state
        
        return self.extraction_agent.extract_information(state)
    
    def _structuring_step(self, state: ProcessingState) -> ProcessingState:
        """Data structuring step"""
        print(f"Starting data structuring for document: {state.document_id}")
        
        if state.errors:
            print(f"Skipping structuring due to previous errors: {state.errors}")
            return state
        
        return self.structuring_agent.structure_data(state)
    
    def _coding_step(self, state: ProcessingState) -> ProcessingState:
        """Clinical coding step"""
        print(f"Starting clinical coding for document: {state.document_id}")
        
        if state.errors:
            print(f"Skipping coding due to previous errors: {state.errors}")
            return state
        
        return self.coding_agent.assign_codes(state)
    
    def _excel_generation_step(self, state: ProcessingState) -> ProcessingState:
        """Excel file generation step"""
        print(f"Starting Excel generation for document: {state.document_id}")
        
        if state.errors:
            print(f"Skipping Excel generation due to previous errors: {state.errors}")
            return state
        
        try:
            # Use coded data if available, otherwise use structured data
            data_to_export = state.coded_data or state.structured_data
            
            if data_to_export:
                output_path = self.excel_generator.generate_excel(
                    data_to_export, 
                    state.document_id
                )
                state.output_file_path = output_path
                state.metadata['excel_generated'] = True
                print(f"Excel file generated: {output_path}")
            else:
                state.errors.append("No data available for Excel generation")
                
        except Exception as e:
            error_msg = f"Excel generation failed: {str(e)}"
            state.errors.append(error_msg)
            print(f"Error in Excel generation: {error_msg}")
        
        return state
    
    def process_prescription(self, input_file_path: str, document_id: str) -> ProcessingState:
        """Process a single prescription file through the complete workflow"""
        
        # Initialize processing state
        initial_state = ProcessingState(
            input_file_path=input_file_path,
            document_id=document_id
        )
        
        print(f"Starting prescription processing workflow for: {document_id}")
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Print final status
        if final_state.errors:
            print(f"Processing completed with errors for {document_id}:")
            for error in final_state.errors:
                print(f"  - {error}")
        else:
            print(f"Processing completed successfully for {document_id}")
            if final_state.output_file_path:
                print(f"Output file: {final_state.output_file_path}")
        
        return final_state
    
    def get_workflow_status(self, state: ProcessingState) -> dict:
        """Get current workflow status"""
        return {
            'document_id': state.document_id,
            'completed_steps': [key for key, value in state.metadata.items() if value],
            'errors': state.errors,
            'has_output': bool(state.output_file_path)
        }