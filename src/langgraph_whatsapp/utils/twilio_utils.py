"""Twilio-specific utilities for WhatsApp integration."""

import base64
import logging
import requests
from typing import Tuple

from src.langgraph_whatsapp.config import TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID

LOGGER = logging.getLogger(__name__)


def validate_twilio_credentials() -> None:
    """Validate that Twilio credentials are configured.
    
    Raises:
        RuntimeError: If Twilio credentials are missing
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN):
        raise RuntimeError("Twilio credentials are missing")


def download_twilio_media(url: str, timeout: int = 30) -> Tuple[bytes, str]:
    """Download media from a Twilio URL.
    
    Args:
        url: The Twilio media URL to download
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (media_bytes, content_type)
        
    Raises:
        RuntimeError: If Twilio credentials are missing
        requests.RequestException: If download fails
    """
    validate_twilio_credentials()
    
    LOGGER.info(f"Downloading media from Twilio URL: {url}")
    
    try:
        resp = requests.get(
            url, 
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), 
            timeout=timeout
        )
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        LOGGER.debug(f"Downloaded {len(resp.content)} bytes with content type: {content_type}")
        
        return resp.content, content_type
        
    except requests.RequestException as e:
        LOGGER.error(f"Failed to download media from {url}: {e}")
        raise


def bytes_to_data_uri(media_bytes: bytes, content_type: str) -> str:
    """Convert media bytes to a data URI.
    
    Args:
        media_bytes: The media content as bytes
        content_type: The MIME type of the media
        
    Returns:
        A data URI string in the format: data:content_type;base64,encoded_data
    """
    b64 = base64.b64encode(media_bytes).decode()
    return f"data:{content_type};base64,{b64}"


def twilio_url_to_data_uri(url: str, content_type: str = None, timeout: int = 20) -> str:
    """Download media from Twilio URL and convert to data URI.
    
    Args:
        url: The Twilio media URL
        content_type: Optional content type override
        timeout: Request timeout in seconds
        
    Returns:
        A data URI string
        
    Raises:
        RuntimeError: If Twilio credentials are missing
        requests.RequestException: If download fails
    """
    media_bytes, detected_content_type = download_twilio_media(url, timeout)
    
    # Use provided content_type or detected one
    mime = content_type or detected_content_type
    
    # Ensure we have a proper image mime type for image processing
    if content_type is None and mime and not mime.startswith('image/'):
        LOGGER.warning(f"Converting non-image MIME type '{mime}' to 'image/jpeg'")
        mime = "image/jpeg"  # Default to jpeg if not an image type
    
    return bytes_to_data_uri(media_bytes, mime)


def extract_filename_from_url(url: str, default_filename: str = "media") -> str:
    """Extract filename from Twilio URL or return default.
    
    Args:
        url: The Twilio URL
        default_filename: Default filename if extraction fails
        
    Returns:
        Extracted or default filename
    """
    try:
        return url.split("/")[-1] if "/" in url else default_filename
    except (AttributeError, IndexError):
        return default_filename 