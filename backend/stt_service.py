"""
Speech-to-Text Service for Pragna-1 A
Uses Groq Whisper API for FREE multilingual transcription
"""
import logging
import io
import os
import tempfile
import requests
import config

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text Service using Groq's FREE Whisper API"""
    
    def __init__(self):
        # Use Groq API for FREE Whisper (no rate limits like OpenAI)
        self.api_key = config.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        self.timeout = config.GROQ_TIMEOUT
        
        if not self.api_key:
            logger.warning("⚠️ GROQ_API_KEY not set - STT service will not work")
        else:
            logger.info("✅ STT Service initialized with Groq Whisper API (FREE)")
    
    def transcribe(self, audio_file, language: str = None) -> tuple:
        """
        Transcribe audio file to text using Groq's FREE Whisper API
        
        Args:
            audio_file: File-like object containing audio data
            language: Optional language hint (e.g., 'en', 'hi', 'kn')
            
        Returns:
            Tuple of (transcribed_text, detected_language)
        """
        if not self.api_key:
            logger.error("Groq API key not configured")
            return None, 'en'
        
        try:
            # Read audio data
            audio_data = audio_file.read()
            
            if len(audio_data) == 0:
                logger.error("Empty audio data received")
                return None, 'en'
            
            logger.info(f"Received audio data: {len(audio_data)} bytes")
            
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Prepare the request for Groq Whisper API
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                # Build form data
                with open(temp_path, 'rb') as f:
                    files = {
                        'file': ('audio.webm', f, 'audio/webm'),
                        'model': (None, 'whisper-large-v3'),  # Groq's free Whisper model
                        'response_format': (None, 'json')
                    }
                    
                    # Add language hint if provided (helps with accuracy)
                    # Groq Whisper requires ISO 639-1 codes (e.g., 'te' not 'telugu')
                    if language and language in config.SUPPORTED_LANGUAGES:
                        # Use the ISO code directly (en, hi, kn, te, etc.)
                        files['language'] = (None, language)
                        logger.info(f"Sending audio to Groq Whisper (language: {language})")
                    else:
                        logger.info("Sending audio to Groq Whisper (auto-detect language)")
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        files=files,
                        timeout=self.timeout
                    )
                
                # Log response for debugging
                if response.status_code != 200:
                    logger.error(f"Groq Whisper API error: {response.status_code} - {response.text}")
                    response.raise_for_status()
                
                result = response.json()
                
                transcribed_text = result.get('text', '').strip()
                
                if not transcribed_text:
                    logger.warning("Empty transcription received")
                    return None, language or 'en'
                
                # Detect language from the transcription
                detected_language = self._detect_language(transcribed_text, language)
                
                logger.info(f"Transcribed: {transcribed_text[:100]}... (lang: {detected_language})")
                
                return transcribed_text, detected_language
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except requests.exceptions.Timeout:
            logger.error("Groq Whisper API request timed out")
            return None, language or 'en'
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq Whisper API error: {e}")
            return None, language or 'en'
            
        except Exception as e:
            logger.error(f"Error in transcribe: {e}", exc_info=True)
            return None, language or 'en'
    
    def _detect_language(self, text: str, hint: str = None) -> str:
        """
        Detect language from text
        Uses simple heuristics based on character ranges
        
        Args:
            text: The transcribed text
            hint: Optional language hint from user
            
        Returns:
            Language code (en, hi, kn, etc.)
        """
        if hint and hint in config.SUPPORTED_LANGUAGES:
            return hint
        
        if not text:
            return 'en'
        
        # Check for Devanagari script (Hindi, Marathi)
        devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        
        # Check for Kannada script
        kannada_chars = sum(1 for c in text if '\u0C80' <= c <= '\u0CFF')
        
        # Check for Telugu script
        telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
        
        # Check for Tamil script
        tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        
        # Check for Malayalam script
        malayalam_chars = sum(1 for c in text if '\u0D00' <= c <= '\u0D7F')
        
        # Check for Bengali script
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        
        # Check for Gujarati script
        gujarati_chars = sum(1 for c in text if '\u0A80' <= c <= '\u0AFF')
        
        # Check for Gurmukhi script (Punjabi)
        gurmukhi_chars = sum(1 for c in text if '\u0A00' <= c <= '\u0A7F')
        
        # Determine language based on character counts
        char_counts = {
            'hi': devanagari_chars,  # Could also be Marathi
            'kn': kannada_chars,
            'te': telugu_chars,
            'ta': tamil_chars,
            'ml': malayalam_chars,
            'bn': bengali_chars,
            'gu': gujarati_chars,
            'pa': gurmukhi_chars
        }
        
        # Find the script with most characters
        max_count = max(char_counts.values())
        
        if max_count > 0:
            for lang, count in char_counts.items():
                if count == max_count:
                    return lang
        
        # Default to English if no Indic script detected
        return 'en'
