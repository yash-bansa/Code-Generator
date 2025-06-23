import os
import sys
from pathlib import Path
from typing import List
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from services.lm_studio_client import LMStudioClient
from workflows.processing_workflow import PharmaProcessingWorkflow
from utils.file_handler import FileHandler

class PharmaAIProcessor:
    """Main application class for processing pharmaceutical prescriptions"""
    
    def __init__(self, lm_studio_url: str = "http://localhost:1234"):
        """Initialize the processor with LM Studio client"""
        self.lm_client = LMStudioClient(base_url=lm_studio_url)
        self.workflow = PharmaProcessingWorkflow(self.lm_client)
        self.file_handler = FileHandler()
        
    def process_single_file(self, input_path: str, output_dir: str = "data/output") -> dict:
        """Process a single prescription file"""
        try:
            # Validate input file
            if not Path(input_path).exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Generate document ID
            document_id = self._generate_document_id(input_path)
            
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Process the file
            result = self.workflow.process_prescription(input_path, document_id)
            
            return {
                'success': len(result.errors) == 0,
                'document_id': document_id,
                'output_file': result.output_file_path,
                'errors': result.errors,
                'metadata': result.metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'document_id': None,
                'output_file': None,
                'errors': [str(e)],
                'metadata': {}
            }
    
    def process_batch(self, input_dir: str, output_dir: str = "data/output") -> List[dict]:
        """Process multiple prescription files from a directory"""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.pdf'}
        input_files = [
            f for f in input_path.iterdir() 
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        
        if not input_files:
            print(f"No image files found in {input_dir}")
            return []
        
        print(f"Found {len(input_files)} files to process")
        
        results = []
        for i, file_path in enumerate(input_files, 1):
            print(f"\nProcessing file {i}/{len(input_files)}: {file_path.name}")
            
            result = self.process_single_file(str(file_path), output_dir)
            results.append(result)
            
            # Print progress
            if result['success']:
                print(f"✓ Successfully processed {file_path.name}")
            else:
                print(f"✗ Failed to process {file_path.name}")
                for error in result['errors']:
                    print(f"  Error: {error}")
        
        return results
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path"""
        file_name = Path(file_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{file_name}_{timestamp}"
    
    def health_check(self) -> dict:
        """Check if all services are healthy"""
        try:
            # Check LM Studio connection
            lm_status = self.lm_client.health_check()
            
            return {
                'lm_studio': lm_status,
                'workflow': True,
                'file_system': True
            }
        except Exception as e:
            return {
                'lm_studio': False,
                'workflow': False,
                'file_system': False,
                'error': str(e)
            }

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Pharma AI Processor - Process prescription images")
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input file or directory path'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='data/output',
        help='Output directory (default: data/output)'
    )
    
    parser.add_argument(
        '--lm-studio-url',
        default='http://localhost:1234',
        help='LM Studio API URL (default: http://localhost:1234)'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process all files in input directory'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Check system health and exit'
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    try:
        processor = PharmaAIProcessor(lm_studio_url=args.lm_studio_url)
    except Exception as e:
        print(f"Failed to initialize processor: {e}")
        sys.exit(1)
    
    # Health check
    if args.health_check:
        print("Performing health check...")
        health_status = processor.health_check()
        
        print(f"LM Studio: {'✓' if health_status['lm_studio'] else '✗'}")
        print(f"Workflow: {'✓' if health_status['workflow'] else '✗'}")
        print(f"File System: {'✓' if health_status['file_system'] else '✗'}")
        
        if not all(health_status.values()):
            print(f"Health check failed: {health_status.get('error', 'Unknown error')}")
            sys.exit(1)
        else:
            print("All systems healthy!")
            sys.exit(0)
    
    # Process files
    try:
        if args.batch:
            print(f"Processing batch from directory: {args.input}")
            results = processor.process_batch(args.input, args.output)
            
            # Print summary
            successful = sum(1 for r in results if r['success'])
            total = len(results)
            
            print(f"\n=== Batch Processing Summary ===")
            print(f"Total files: {total}")
            print(f"Successful: {successful}")
            print(f"Failed: {total - successful}")
            print(f"Success rate: {successful/total*100:.1f}%" if total > 0 else "N/A")
            
        else:
            print(f"Processing single file: {args.input}")
            result = processor.process_single_file(args.input, args.output)
            
            if result['success']:
                print(f"✓ Processing completed successfully!")
                print(f"Output file: {result['output_file']}")
            else:
                print(f"✗ Processing failed:")
                for error in result['errors']:
                    print(f"  - {error}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()