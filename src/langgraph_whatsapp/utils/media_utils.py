"""Media utilities for content type handling and media processing."""

import logging
from typing import Optional

LOGGER = logging.getLogger(__name__)


def clean_content_type(content_type: str) -> str:
    """Clean content type by removing parameters and normalizing.
    
    Args:
        content_type: Raw content type string (e.g., "audio/ogg; codecs=opus")
        
    Returns:
        Cleaned content type (e.g., "audio/ogg")
    """
    if not content_type:
        return ""
    return content_type.split(';')[0].strip().lower()


def get_file_extension_from_content_type(content_type: str) -> str:
    """Map content type to file extension.
    
    Args:
        content_type: The MIME type of the file
        
    Returns:
        Appropriate file extension for the content type
    """
    content_type_map = {
        # Audio formats
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/mp4': '.mp4',
        'audio/m4a': '.m4a',
        'audio/wav': '.wav',
        'audio/wave': '.wav',
        'audio/x-wav': '.wav',
        'audio/flac': '.flac',
        'audio/ogg': '.ogg',
        'audio/webm': '.webm',
        'audio/x-m4a': '.m4a',
        'audio/aac': '.m4a',  # AAC often uses .m4a container
        'audio/opus': '.ogg',  # Opus is often in OGG container
        'audio/x-opus': '.ogg',
        'audio/vorbis': '.ogg',
        'audio/x-vorbis': '.ogg',
        'audio/amr': '.m4a',  # AMR can be transcoded to m4a
        'audio/3gpp': '.m4a',  # 3GPP audio
        'audio/x-aiff': '.wav',  # AIFF can be handled as WAV
        'audio/aiff': '.wav',
        # WhatsApp specific formats
        'audio/ogg; codecs=opus': '.ogg',
        'application/ogg': '.ogg',
        
        # Image formats
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/svg+xml': '.svg',
        
        # Video formats
        'video/mp4': '.mp4',
        'video/webm': '.webm',
        'video/ogg': '.ogv',
        'video/avi': '.avi',
        'video/mov': '.mov',
        'video/wmv': '.wmv',
        'video/flv': '.flv',
        
        # Document formats
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'application/json': '.json',
        'application/xml': '.xml',
        'text/html': '.html',
        'text/css': '.css',
        'application/javascript': '.js',
    }
    
    clean_content_type_str = clean_content_type(content_type)
    return content_type_map.get(clean_content_type_str, '.bin')  # Default to .bin for unknown types


def is_audio_content_type(content_type: str) -> bool:
    """Check if content type represents audio.
    
    Args:
        content_type: The MIME type to check
        
    Returns:
        True if content type is audio, False otherwise
    """
    clean_type = clean_content_type(content_type)
    return clean_type.startswith('audio/') or clean_type == 'application/ogg'


def is_image_content_type(content_type: str) -> bool:
    """Check if content type represents an image.
    
    Args:
        content_type: The MIME type to check
        
    Returns:
        True if content type is image, False otherwise
    """
    clean_type = clean_content_type(content_type)
    return clean_type.startswith('image/')


def is_video_content_type(content_type: str) -> bool:
    """Check if content type represents video.
    
    Args:
        content_type: The MIME type to check
        
    Returns:
        True if content type is video, False otherwise
    """
    clean_type = clean_content_type(content_type)
    return clean_type.startswith('video/')


def get_media_type_category(content_type: str) -> Optional[str]:
    """Get the general category of media type.
    
    Args:
        content_type: The MIME type to categorize
        
    Returns:
        Media category: 'audio', 'image', 'video', or None for unknown types
    """
    if is_audio_content_type(content_type):
        return 'audio'
    elif is_image_content_type(content_type):
        return 'image'
    elif is_video_content_type(content_type):
        return 'video'
    return None


def ensure_valid_filename(filename: str, content_type: str = None, default_name: str = "media") -> str:
    """Ensure filename has appropriate extension based on content type.
    
    Args:
        filename: Original filename
        content_type: MIME type of the file
        default_name: Default name if filename is invalid
        
    Returns:
        Filename with appropriate extension
    """
    if not filename or filename.isspace():
        filename = default_name
    
    # If we have content type, ensure extension matches
    if content_type:
        expected_extension = get_file_extension_from_content_type(content_type)
        
        # Check if filename already has a proper extension
        if '.' in filename:
            current_extension = '.' + filename.rsplit('.', 1)[1].lower()
            # If extension doesn't match expected, replace it
            if current_extension != expected_extension:
                base_name = filename.rsplit('.', 1)[0]
                filename = base_name + expected_extension
        else:
            # No extension, add the expected one
            filename = filename + expected_extension
    else:
        # No content type provided, ensure filename has some extension
        if '.' not in filename:
            filename = filename + '.bin'
    
    return filename 