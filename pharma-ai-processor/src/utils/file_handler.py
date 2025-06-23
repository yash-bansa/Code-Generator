import os
import shutil
from pathlib import Path
from typing import List, Union, Optional
import mimetypes

class FileHandler:
    """Utility class for handling file operations"""
    
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
    SUPPORTED_DOCUMENT_FORMATS = {'.pdf'}
    
    def __init__(self):
        pass
    
    def validate_input_file(self, file_path: str) -> bool:
        """Validate if input file is supported format"""
        path = Path(file_path)
        
        if not path.exists():
            return False
        
        if not path.is_file():
            return False
        
        file_extension = path.suffix.lower()
        supported_formats = self.SUPPORTED_IMAGE_FORMATS | self.SUPPORTED_DOCUMENT_FORMATS
        
        return file_extension in supported_formats
    
    def get_file_type(self, file_path: str) -> Optional[str]:
        """Get file type (image/document) from file path"""
        path = Path(file_path)
        file_extension = path.suffix.lower()
        
        if file_extension in self.SUPPORTED_IMAGE_FORMATS:
            return 'image'
        elif file_extension in self.SUPPORTED_DOCUMENT_FORMATS:
            return 'document'
        else:
            return None
    
    def find_input_files(self, directory: str) -> List[str]:
        """Find all supported input files in a directory"""
        dir_path = Path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        input_files = []
        supported_formats = self.SUPPORTED_IMAGE_FORMATS | self.SUPPORTED_DOCUMENT_FORMATS
        
        for file_path in dir_path.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() in supported_formats):
                input_files.append(str(file_path))
        
        return sorted(input_files)
    
    def create_output_directory(self, output_path: str) -> bool:
        """Create output directory if it doesn't exist"""
        try:
            Path(output_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Failed to create output directory {output_path}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get detailed information about a file"""
        path = Path(file_path)
        
        if not path.exists():
            return {'error': 'File not found'}
        
        stat = path.stat()
        
        return {
            'name': path.name,
            'stem': path.stem,
            'suffix': path.suffix,
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': stat.st_mtime,
            'is_file': path.is_file(),
            'is_dir': path.is_dir(),
            'file_type': self.get_file_type(str(path)),
            'mime_type': mimetypes.guess_type(str(path))[0]
        }
    
    def copy_file(self, source: str, destination: str) -> bool:
        """Copy file from source to destination"""
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            print(f"Failed to copy file from {source} to {destination}: {e}")
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        """Move file from source to destination"""
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            return True
        except Exception as e:
            print(f"Failed to move file from {source} to {destination}: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        try:
            Path(file_path).unlink()
            return True
        except Exception as e:
            print(f"Failed to delete file {file_path}: {e}")
            return False
    
    def cleanup_temp_files(self, temp_dir: str) -> bool:
        """Clean up temporary files in a directory"""
        try:
            temp_path = Path(temp_dir)
            if temp_path.exists() and temp_path.is_dir():
                shutil.rmtree(temp_path)
            return True
        except Exception as e:
            print(f"Failed to cleanup temp directory {temp_dir}: {e}")
            return False
    
    def ensure_unique_filename(self, file_path: str) -> str:
        """Ensure filename is unique by adding counter if needed"""
        path = Path(file_path)
        
        if not path.exists():
            return str(path)
        
        counter = 1
        while True:
            new_name = f"{path.stem}_{counter}{path.suffix}"
            new_path = path.parent / new_name
            
            if not new_path.exists():
                return str(new_path)
            
            counter += 1
    
    def get_directory_size(self, directory: str) -> dict:
        """Get total size of all files in a directory"""
        dir_path = Path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            return {'error': 'Directory not found'}
        
        total_size = 0
        file_count = 0
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'directory': str(dir_path)
        }