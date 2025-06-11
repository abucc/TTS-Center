import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_file(url, filepath):
    """Download a file from URL to filepath"""
    try:
        logger.info(f"Downloading {url} to {filepath}")
        urllib.request.urlretrieve(url, filepath)
        logger.info(f"Successfully downloaded {filepath}")
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        raise

def main():
    model_dir = "/app/models"
    os.makedirs(model_dir, exist_ok=True)
    
    # Model URLs from Kokoro ONNX releases
    model_urls = {
        "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
    }
    
    for filename, url in model_urls.items():
        filepath = os.path.join(model_dir, filename)
        
        # Skip if file already exists and is not empty
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            logger.info(f"Model file {filename} already exists, skipping download")
            continue
            
        try:
            download_file(url, filepath)
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            # Continue with other downloads
            continue
    
    logger.info("Model download process completed")

if __name__ == "__main__":
    main()
