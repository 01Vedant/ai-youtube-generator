"""
TTS Provider abstraction with fallback chain:
1. Azure Cognitive Services (if AZURE_TTS_KEY set)
2. ElevenLabs (if ELEVEN_API_KEY set)
3. Fallback: Synthetic placeholder WAV (always works)
"""
import os
import struct
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TTSProvider:
    """Text-to-Speech provider with automatic fallback chain."""
    
    def __init__(self):
        self.azure_key = os.getenv("AZURE_TTS_KEY")
        self.azure_region = os.getenv("AZURE_TTS_REGION", "westeurope")
        self.azure_voice_hi = os.getenv("AZURE_TTS_VOICE_HI", "hi-IN-SwaraNeural")
        
        self.eleven_key = os.getenv("ELEVEN_API_KEY")
        self.eleven_voice_hi = os.getenv("ELEVEN_VOICE_ID_HINDI", "")
        
        # Determine active provider
        if self.azure_key and self.azure_region:
            self.provider = "azure"
        elif self.eleven_key:
            self.provider = "elevenlabs"
        else:
            self.provider = "fallback"
        
        logger.info(f"TTS Provider initialized: {self.provider}")
    
    def synthesize(
        self,
        text: str,
        *,
        lang: str = "hi",
        voice_hint: Optional[str] = None,
        ssml: Optional[str] = None,
        out_path: Path
    ) -> Dict[str, Any]:
        """
        Synthesize text to audio file.
        
        Args:
            text: Plain text to synthesize (used if ssml is None)
            lang: Language code ("hi" for Hindi)
            voice_hint: Voice preference ("hi_female_soft" or similar)
            ssml: SSML string (if provided, overrides plain text)
            out_path: Output path for audio file (will be .wav)
        
        Returns:
            Dict with keys: provider, voice, path, duration_sec
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = ssml if ssml else text
        
        if self.provider == "azure":
            return self._azure_synthesize(content, lang, out_path)
        elif self.provider == "elevenlabs":
            return self._eleven_synthesize(text, lang, out_path)  # ElevenLabs doesn't use SSML
        else:
            return self._fallback_synthesize(text, lang, out_path)
    
    def _azure_synthesize(self, content: str, lang: str, out_path: Path) -> Dict[str, Any]:
        """Azure Cognitive Services TTS."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            speech_config = speechsdk.SpeechConfig(
                subscription=self.azure_key,
                region=self.azure_region
            )
            
            audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_path))
            
            # Determine if content is SSML or plain text
            if content.strip().startswith('<speak'):
                speech_config.speech_synthesis_language = lang + "-IN"
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                result = synthesizer.speak_ssml_async(content).get()
            else:
                speech_config.speech_synthesis_voice_name = self.azure_voice_hi
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                result = synthesizer.speak_text_async(content).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                duration = len(result.audio_data) / (16000 * 2)  # 16kHz, 16-bit
                logger.info(f"Azure TTS: synthesized {duration:.2f}s to {out_path}")
                return {
                    "provider": "azure",
                    "voice": self.azure_voice_hi,
                    "path": str(out_path),
                    "duration_sec": duration
                }
            else:
                logger.warning(f"Azure TTS failed: {result.reason}, falling back")
                return self._fallback_synthesize(content, lang, out_path)
        
        except Exception as e:
            logger.warning(f"Azure TTS error: {e}, falling back")
            return self._fallback_synthesize(content, lang, out_path)
    
    def _eleven_synthesize(self, text: str, lang: str, out_path: Path) -> Dict[str, Any]:
        """ElevenLabs TTS."""
        try:
            import requests
            
            if not self.eleven_voice_hi:
                raise ValueError("ELEVEN_VOICE_ID_HINDI not set")
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.eleven_voice_hi}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.eleven_key
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.6,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # ElevenLabs returns MP3, convert to WAV
            mp3_path = out_path.with_suffix('.mp3')
            mp3_path.write_bytes(response.content)
            
            # Convert MP3 to WAV using pydub
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(str(mp3_path))
            audio = audio.set_channels(1).set_frame_rate(22050)  # Mono, 22050 Hz
            audio.export(str(out_path), format="wav")
            mp3_path.unlink()  # Clean up MP3
            
            duration = len(audio) / 1000.0
            logger.info(f"ElevenLabs TTS: synthesized {duration:.2f}s to {out_path}")
            return {
                "provider": "elevenlabs",
                "voice": self.eleven_voice_hi,
                "path": str(out_path),
                "duration_sec": duration
            }
        
        except Exception as e:
            logger.warning(f"ElevenLabs TTS error: {e}, falling back")
            return self._fallback_synthesize(text, lang, out_path)
    
    def _fallback_synthesize(self, text: str, lang: str, out_path: Path) -> Dict[str, Any]:
        """
        Fallback: Generate synthetic placeholder WAV.
        Estimates duration from text length (~13 Devanagari chars/sec for devotional pace).
        Always produces valid 22050 Hz mono PCM WAV.
        """
        # Strip SSML tags if present
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Estimate duration: ~13 chars/sec for calm Hindi devotional narration
        char_count = len(clean_text)
        estimated_duration = max(1.0, char_count / 13.0)
        
        # Generate silent WAV with proper headers
        sample_rate = 22050
        num_samples = int(sample_rate * estimated_duration)
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = num_samples * block_align
        
        wav = io.BytesIO()
        # RIFF header
        wav.write(b'RIFF')
        wav.write(struct.pack('<I', 36 + data_size))
        wav.write(b'WAVE')
        # fmt chunk
        wav.write(b'fmt ')
        wav.write(struct.pack('<I', 16))  # fmt chunk size
        wav.write(struct.pack('<H', 1))   # PCM format
        wav.write(struct.pack('<H', num_channels))
        wav.write(struct.pack('<I', sample_rate))
        wav.write(struct.pack('<I', byte_rate))
        wav.write(struct.pack('<H', block_align))
        wav.write(struct.pack('<H', bits_per_sample))
        # data chunk
        wav.write(b'data')
        wav.write(struct.pack('<I', data_size))
        wav.write(b'\x00' * data_size)  # Silence
        
        out_path.write_bytes(wav.getvalue())
        
        logger.info(f"Fallback TTS: generated {estimated_duration:.2f}s placeholder to {out_path}")
        return {
            "provider": "fallback",
            "voice": "synthetic_placeholder",
            "path": str(out_path),
            "duration_sec": estimated_duration
        }
