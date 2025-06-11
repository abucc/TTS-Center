#!/usr/bin/env python3
"""
Model downloader for Kokoro ONNX TTS
Downloads the required model files if they don't exist
"""

import os
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_URLS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
}

def download_file(url: str, filepath: Path) -> bool:
    """Download a file from URL to filepath"""
    try:
        logger.info(f"Downloading {url} to {filepath}")
        urllib.request.urlretrieve(url, filepath)
        logger.info(f"Successfully downloaded {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def download_models(model_path: str = "/app/models") -> bool:
    """Download all required model files"""
    model_dir = Path(model_path)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    success = True
    for filename, url in MODEL_URLS.items():
        filepath = model_dir / filename
        
        if filepath.exists():
            logger.info(f"Model file {filepath} already exists, skipping download")
            continue
            
        if not download_file(url, filepath):
            success = False
    
    return success

if __name__ == "__main__":
    model_path = os.getenv("MODEL_PATH", "/app/models")
    success = download_models(model_path)
    
    if success:
        logger.info("All models downloaded successfully")
    else:
        logger.error("Some models failed to download")
        exit(1)
