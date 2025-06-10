import os
import logging
from openai import AsyncOpenAI
import io

from .media_utils import ensure_valid_filename

LOGGER = logging.getLogger(__name__)

async def speech_to_text(audio_bytes: bytes, filename: str = "audio.mp3", content_type: str = None) -> str:
    """
    Transcribes audio bytes into text using OpenAI's Whisper API.

    Args:
        audio_bytes: The byte content of the audio file.
        filename: The original filename, used to help Whisper with the format.
        content_type: The MIME type of the audio file (optional, for better format detection)

    Returns:
        The transcribed text as a string.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        LOGGER.error("OPENAI_API_KEY environment variable not set.")
        # Decide on error handling: raise an exception or return an error message
        raise ValueError("OpenAI API key not configured.")

    client = AsyncOpenAI(api_key=api_key)

    try:
        # Validate input
        if not audio_bytes:
            raise ValueError("Audio bytes cannot be empty")
        
        if len(audio_bytes) < 100:  # Very small files are likely not valid audio
            raise ValueError(f"Audio file too small ({len(audio_bytes)} bytes), likely not valid audio")
        
        # The Whisper API expects a file-like object.
        # We can use io.BytesIO to treat the byte string as a file.
        # The 'name' attribute of the tuple for the file is important for the API to infer the file type.
        audio_file_like = io.BytesIO(audio_bytes)
        
        # Use the new utility functions for consistent filename handling
        filename = ensure_valid_filename(filename, content_type, "audio")
        
        LOGGER.info(f"Transcribing audio file: {filename} with content type: {content_type}")
        LOGGER.debug(f"Audio file size: {len(audio_bytes)} bytes")
        
        # Note: The OpenAI Python client library handles the multipart/form-data encoding.
        # We pass a tuple: (filename, file-like object)
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_file_like), # Pass as a tuple
            response_format="text" 
        )
        
        LOGGER.info(f"Transcription successful for {filename}")
        # The response_format="text" should return a plain string.
        # If it were JSON, it would be transcript.text
        return str(transcript) 
    except Exception as e:
        LOGGER.error(f"Error during OpenAI API call for speech-to-text: {e}", exc_info=True)
        
        # Provide more specific error information
        error_msg = f"Failed to transcribe audio (filename: {filename}, content_type: {content_type}, size: {len(audio_bytes) if audio_bytes else 0} bytes)"
        
        # Check if it's an OpenAI API error with specific handling
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            if e.response.status_code == 400:
                error_msg += f" - Bad Request: {str(e)}"
            elif e.response.status_code == 413:
                error_msg += f" - File too large: {str(e)}"
            else:
                error_msg += f" - API Error ({e.response.status_code}): {str(e)}"
        else:
            error_msg += f" - {str(e)}"
        
        LOGGER.error(error_msg)
        # Depending on how you want to handle errors, you might raise the exception
        # or return a specific error message/code.
        raise # Re-raise the exception to be handled by the caller
