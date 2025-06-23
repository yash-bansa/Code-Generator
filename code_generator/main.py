#!/usr/bin/env python3
"""
AI Code Generator - Main Entry Point

This module provides the main interface for the AI-powered code generation system.
It allows users to upload configuration files and automatically generates code modifications
for data loading processes using intelligent agents.

Usage:
    python main.py --config config.json --project /path/to/project
    python main.py --interactive
    python main.py --validate-setup
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from datetime import datetime

# Import workflow and utilities
from workflow.graph import CodeGenerationWorkflow, run_code_generation_workflow
from utils.file_handler import FileHandler
from config.settings import Settings
from utils.llm_client import LMStudioClient


# Configure logging
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Set up handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    else:
        # Default log file with timestamp
        default_log_file = log_dir / f"ai_code_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(default_log_file))
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Suppress verbose logs from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


class AICodeGenerator:
    """Main class for AI Code Generator application"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = logging.getLogger(__name__)
        self.workflow = None
        
    def initialize(self) -> bool:
        """Initialize the AI Code Generator"""
        try:
            self.logger.info("Initializing AI Code Generator...")
            
            # Validate settings
            if not self._validate_settings():
                return False
            
            # Test LLM connection
            if not self._test_llm_connection():
                return False
            
            # Initialize workflow
            self.workflow = CodeGenerationWorkflow()
            
            self.logger.info("AI Code Generator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Code Generator: {e}")
            return False
    
    def _validate_settings(self) -> bool:
        """Validate application settings"""
        try:
            # Check if required directories exist
            required_dirs = ["output", "logs", "config"]
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Created directory: {dir_path}")
            
            # Validate LLM settings
            if not self.settings.LM_STUDIO_BASE_URL:
                self.logger.error("LLM_BASE_URL not configured in settings")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Settings validation failed: {e}")
            return False
    
    def _test_llm_connection(self) -> bool:
        """Test connection to LLM Studio"""
        try:
            self.logger.info("Testing LLM connection...")
            
            llm_client = LMStudioClient()
            
            # Test with a simple prompt
            test_response = llm_client.chat_completion(
            messages=[{"role": "user", "content": "Test connection. Please respond with 'Connection successful'."}],
            max_tokens=50
            )

            
            if test_response and "successful" in test_response.lower():
                self.logger.info("LLM connection test successful")
                return True
            else:
                self.logger.warning("LLM connection test returned unexpected response")
                return True  # Still proceed as LLM might be working
                
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {e}")
            self.logger.error("Please ensure LM Studio is running and accessible")
            return False
    
    def process_config_file(self, config_path: str, project_path: str) -> Dict[str, Any]:
        """Process a configuration file and generate code modifications"""
        
        self.logger.info(f"Processing configuration: {config_path}")
        self.logger.info(f"Target project: {project_path}")
        
        try:
            # Validate inputs
            config_file = Path(config_path)
            project_dir = Path(project_path)
            
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            if not project_dir.exists():
                raise FileNotFoundError(f"Project directory not found: {project_path}")
            
            # Load and validate configuration
            config_data = self._load_and_validate_config(config_file)
            if not config_data:
                return {"status": "failed", "error": "Invalid configuration file"}
            
            # Run the workflow
            self.logger.info("Starting AI code generation workflow...")
            
            results = run_code_generation_workflow(
                config_file_path=str(config_file),
                project_path=str(project_dir)
            )
            
            # Log results
            self._log_workflow_results(results)
            
            return results
            
        except Exception as e:
            error_msg = f"Error processing configuration: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            
            return {
                "status": "failed",
                "error": error_msg,
                "files_modified": 0
            }
    
    def _load_and_validate_config(self, config_file: Path) -> Optional[Dict[str, Any]]:
        """Load and validate configuration file"""
        try:
            # Load configuration
            config_data = FileHandler.read_json_file(config_file)
            
            if not config_data:
                self.logger.error("Failed to load configuration file")
                return None
            
            # Basic validation
            required_fields = ["project", "modifications"]
            for field in required_fields:
                if field not in config_data:
                    self.logger.error(f"Missing required field in config: {field}")
                    return None
            
            self.logger.info("Configuration file loaded and validated successfully")
            return config_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return None
    
    def _log_workflow_results(self, results: Dict[str, Any]):
        """Log workflow execution results"""
        status = results.get("status", "unknown")
        files_modified = results.get("files_modified", 0)
        errors = results.get("errors", [])
        
        self.logger.info(f"Workflow Status: {status}")
        self.logger.info(f"Files Modified: {files_modified}")
        
        if errors:
            self.logger.warning(f"Errors encountered: {len(errors)}")
            for error in errors:
                self.logger.warning(f"  - {error}")
        
        if status == "completed":
            self.logger.info("✅ Code generation completed successfully!")
            if files_modified > 0:
                self.logger.info(f"📁 Check the 'output/generated_code' directory for {files_modified} modified files")
        else:
            self.logger.error("❌ Code generation failed!")
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("\n🤖 AI Code Generator - Interactive Mode")
        print("=" * 50)
        
        while True:
            try:
                print("\nOptions:")
                print("1. Process configuration file")
                print("2. Validate setup")
                print("3. View recent logs")
                print("4. Exit")
                
                choice = input("\nSelect an option (1-4): ").strip()
                
                if choice == "1":
                    self._interactive_process_config()
                elif choice == "2":
                    self._interactive_validate_setup()
                elif choice == "3":
                    self._interactive_view_logs()
                elif choice == "4":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please select 1-4.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _interactive_process_config(self):
        """Interactive configuration processing"""
        try:
            config_path = input("Enter configuration file path: ").strip()
            project_path = input("Enter project directory path: ").strip()
            
            if not config_path or not project_path:
                print("❌ Both paths are required!")
                return
            
            print("\n🚀 Starting code generation process...")
            results = self.process_config_file(config_path, project_path)
            
            # Display results
            print(f"\n📊 Results:")
            print(f"Status: {results.get('status', 'unknown')}")
            print(f"Files Modified: {results.get('files_modified', 0)}")
            
            if results.get('errors'):
                print(f"Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:  # Show first 3 errors
                    print(f"  - {error}")
                if len(results['errors']) > 3:
                    print(f"  ... and {len(results['errors']) - 3} more errors")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def _interactive_validate_setup(self):
        """Interactive setup validation"""
        print("\n🔍 Validating setup...")
        
        # Check directories
        dirs_to_check = ["agents", "workflow", "utils", "config", "output"]
        for dir_name in dirs_to_check:
            if Path(dir_name).exists():
                print(f"✅ {dir_name}/ directory exists")
            else:
                print(f"❌ {dir_name}/ directory missing")
        
        # Check key files
        files_to_check = [
            "workflow/graph.py",
            "agents/parser_agent.py",
            "agents/code_identifier_agent.py",
            "agents/code_generator_agent.py",
            "agents/code_validator_agent.py",
            "utils/llm_client.py"
        ]
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                print(f"✅ {file_path} exists")
            else:
                print(f"❌ {file_path} missing")
        
        # Test LLM connection
        if self._test_llm_connection():
            print("✅ LLM connection successful")
        else:
            print("❌ LLM connection failed")
    
    def _interactive_view_logs(self):
        """Interactive log viewer"""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                print("❌ No logs directory found")
                return
            
            log_files = list(log_dir.glob("*.log"))
            if not log_files:
                print("❌ No log files found")
                return
            
            # Get most recent log file
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            
            print(f"\n📄 Showing last 20 lines from: {latest_log.name}")
            print("-" * 50)
            
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
                    
        except Exception as e:
            print(f"❌ Error reading logs: {e}")


def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "project": {
            "name": "data_pipeline_update",
            "description": "Update data loading pipeline with new configurations",
            "version": "1.0.0"
        },
        "modifications": {
            "data_sources": {
                "database": {
                    "host": "new-db-server.com",
                    "port": 5432,
                    "database": "analytics_db",
                    "schema": "public"
                },
                "file_sources": [
                    {
                        "type": "csv",
                        "path": "/data/new_files/",
                        "pattern": "*.csv"
                    }
                ]
            },
            "transformations": [
                {
                    "type": "column_mapping",
                    "old_column": "customer_id",
                    "new_column": "client_id"
                },
                {
                    "type": "data_type_change",
                    "column": "created_date",
                    "old_type": "string",
                    "new_type": "datetime"
                }
            ],
            "output_format": {
                "type": "parquet",
                "compression": "snappy",
                "partition_by": ["date", "region"]
            }
        },
        "target_files": [
            "data_loader.py",
            "pipeline.py",
            "config.py"
        ]
    }
    
    # Save sample config
    config_dir = Path("examples")
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "sample_config.json"
    with open(config_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"✅ Sample configuration created: {config_file}")


def main():
    """Main entry point"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Code Generator - Automatically modify code based on configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --config examples/sample_config.json --project examples/sample_project
  python main.py --interactive
  python main.py --validate-setup
  python main.py --create-sample-config
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration JSON file"
    )
    
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Path to target project directory"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--validate-setup",
        action="store_true",
        help="Validate system setup and dependencies"
    )
    
    parser.add_argument(
        "--create-sample-config",
        action="store_true",
        help="Create a sample configuration file"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Custom log file path"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    # Handle special commands
    if args.create_sample_config:
        create_sample_config()
        return
    
    # Initialize the AI Code Generator
    ai_generator = AICodeGenerator()
    
    print("🤖 AI Code Generator v1.0.0")
    print("Automated code modification using intelligent agents")
    print("=" * 55)
    
    # Initialize the system
    if not ai_generator.initialize():
        print("❌ Failed to initialize AI Code Generator")
        print("Please check the logs for details")
        sys.exit(1)
    
    try:
        if args.validate_setup:
            # Validate setup
            ai_generator._interactive_validate_setup()
            
        elif args.interactive:
            # Run in interactive mode
            ai_generator.interactive_mode()
            
        elif args.config and args.project:
            # Process configuration file
            print(f"\n🚀 Processing configuration: {args.config}")
            print(f"📁 Target project: {args.project}")
            
            results = ai_generator.process_config_file(args.config, args.project)
            
            # Display results
            print(f"\n📊 Final Results:")
            print(f"Status: {results.get('status', 'unknown')}")
            print(f"Files Modified: {results.get('files_modified', 0)}")
            
            if results.get('status') == 'completed':
                print("✅ Code generation completed successfully!")
                print("📁 Check the 'output/generated_code' directory for modified files")
            else:
                print("❌ Code generation failed!")
                if results.get('errors'):
                    print("Errors:")
                    for error in results['errors']:
                        print(f"  - {error}")
            
        else:
            # Show help if no valid arguments provided
            parser.print_help()
            print("\n💡 Tip: Use --interactive for a guided experience")
            print("💡 Tip: Use --create-sample-config to generate a sample configuration")
            
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        print(f"❌ Unexpected error: {e}")
        print("Please check the logs for details")
        sys.exit(1)


if __name__ == "__main__":
    main()