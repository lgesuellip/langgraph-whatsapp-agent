# channel.py
import base64, logging, requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from fastapi import Request, HTTPException
from twilio.twiml.messaging_response import MessagingResponse

from src.langgraph_whatsapp.agent import Agent
from src.langgraph_whatsapp.config import TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_WHATSAPP_NUMBER
from twilio.rest import Client
from src.langgraph_whatsapp.utils.speech_to_text import speech_to_text
from src.langgraph_whatsapp.utils.twilio_utils import twilio_url_to_data_uri, download_twilio_media, extract_filename_from_url
from src.langgraph_whatsapp.utils.media_utils import is_audio_content_type, is_image_content_type

LOGGER = logging.getLogger("whatsapp")


async def twilio_url_to_audio_transcript(url: str, content_type: str) -> Optional[str]:
    """Download the Twilio audio URL and convert to text transcript."""
    try:
        LOGGER.info(f"Processing audio from URL: {url}")
        
        # Use shared utility for downloading
        audio_bytes, _ = download_twilio_media(url, timeout=30)
        
        # Extract filename using shared utility
        filename = extract_filename_from_url(url, "audio.ogg")
        
        # Transcribe audio to text
        transcript = await speech_to_text(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type
        )
        
        if transcript:
            LOGGER.info(f"Audio transcribed successfully: {transcript[:50]}...")
            return transcript
        else:
            LOGGER.warning("Audio transcription returned empty result")
            return None
            
    except Exception as err:
        LOGGER.error(f"Failed to process audio from {url}: {err}")
        return "[Audio transcription failed]"


async def process_twilio_media(form_data) -> tuple[List[Dict], List[str]]:
    """Process all media files (images and audio) from Twilio form data.
    
    Returns:
        tuple: (images_list, audio_transcripts_list)
    """
    images = []
    audio_transcripts = []
    
    for i in range(int(form_data.get("NumMedia", "0"))):
        url = form_data.get(f"MediaUrl{i}", "")
        ctype = form_data.get(f"MediaContentType{i}", "")
        
        if url and is_image_content_type(ctype):
            try:
                images.append({
                    "url": url,
                    "data_uri": twilio_url_to_data_uri(url, ctype),
                })
            except Exception as err:
                LOGGER.error("Failed to download image %s: %s", url, err)
                
        elif url and is_audio_content_type(ctype):
            transcript = await twilio_url_to_audio_transcript(url, ctype)
            if transcript:
                audio_transcripts.append(transcript)
    
    return images, audio_transcripts


async def prepare_message_content(form_data) -> tuple[str, List[Dict]]:
    """Prepare the complete message content including text, audio transcripts, and images.
    
    Returns:
        tuple: (final_content_string, images_list)
    """
    content = form_data.get("Body", "").strip()
    images, audio_transcripts = await process_twilio_media(form_data)
    
    # Combine text content with audio transcripts
    if audio_transcripts:
        # If we have audio transcripts, prepend them to the message
        full_content = "\n\n".join(audio_transcripts)
        if content:
            full_content += f"\n\nText message: {content}"
        content = full_content
    
    return content, images


class WhatsAppAgent(ABC):
    @abstractmethod
    async def handle_message(self, request: Request) -> str: ...

class WhatsAppAgentTwilio(WhatsAppAgent):
    def __init__(self) -> None:
        if not (TWILIO_AUTH_TOKEN and TWILIO_ACCOUNT_SID):
            raise ValueError("Twilio credentials are not configured")
        self.agent = Agent()
        self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.twilio_whatsapp_number = TWILIO_WHATSAPP_NUMBER

    async def handle_message(self, request: Request) -> str:
        form = await request.form()

        sender = form.get("From", "").strip()
        if not sender:
            raise HTTPException(400, detail="Missing 'From' in request form")

        # Process message content and media
        content, images = await prepare_message_content(form)

        # Assemble payload for the LangGraph agent
        input_data = {
            "id": sender,
            "user_message": content,
        }
        if images:
            # Pass all images to the agent
            input_data["images"] = [
                {"image_url": {"url": img["data_uri"]}} for img in images
            ]

        reply = await self.agent.invoke(**input_data)

        twiml = MessagingResponse()
        twiml.message(reply)
        return str(twiml)
    
    async def process_message(self, request: Request) -> str:
        """Process a WhatsApp message and return just the text response (no TwiML)"""
        form = await request.form()

        sender = form.get("From", "").strip()
        if not sender:
            raise HTTPException(400, detail="Missing 'From' in request form")

        # Process message content and media
        content, images = await prepare_message_content(form)

        # Assemble payload for the LangGraph agent
        input_data = {
            "id": sender,
            "user_message": content,
        }
        if images:
            # Pass all images to the agent
            input_data["images"] = [
                {"image_url": {"url": img["data_uri"]}} for img in images
            ]

        reply = await self.agent.invoke(**input_data)
        return reply
    
    async def send_whatsapp_message(self, to_number: str, message: str, from_number: str = None):
        """Send a WhatsApp message using Twilio API"""
        try:
            # Use provided from_number or the one from environment/first message
            whatsapp_from = from_number or self.twilio_whatsapp_number
            
            if not whatsapp_from:
                raise ValueError("WhatsApp from number not configured")
            
            # Ensure numbers are in WhatsApp format
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            if not whatsapp_from.startswith("whatsapp:"):
                whatsapp_from = f"whatsapp:{whatsapp_from}"
            
            # Send message via Twilio API
            message_instance = self.twilio_client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=to_number
            )
            
            LOGGER.info(f"Message sent successfully. SID: {message_instance.sid}")
            return message_instance.sid
            
        except Exception as e:
            LOGGER.error(f"Failed to send WhatsApp message: {str(e)}")
            raise
