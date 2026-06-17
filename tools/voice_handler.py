"""
Gestione vocali Telegram → trascrizione Whisper → testo
"""
import os
import logging
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non trovata in .env")
        self.client = OpenAI(api_key=api_key)
        self.tmp_dir = Path(".tmp")
        self.tmp_dir.mkdir(exist_ok=True)

    async def transcribe_voice(self, file_path: str, language: str = "it") -> str:
        """
        Trascrivi un file audio con OpenAI Whisper.

        Args:
            file_path: percorso locale del file audio (.ogg, .mp3, .wav, .m4a)
            language: lingua ISO 639-1 (default: "it" per italiano)

        Returns:
            testo trascritto in italiano

        Raises:
            FileNotFoundError: se il file non esiste
            ValueError: se il file è > 25MB
        """
        # Verifica file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File audio non trovato: {file_path}")

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 25:
            raise ValueError(
                f"File audio troppo grande ({file_size_mb:.1f}MB). "
                "Limite Whisper: 25MB"
            )

        logger.info(f"Trascrizione vocale: {file_path} ({file_size_mb:.1f}MB)")

        try:
            with open(file_path, "rb") as f:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                    temperature=0.0  # max consistency
                )
            text = transcript.text.strip()
            logger.info(f"✓ Trascritto: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Errore Whisper: {e}")
            raise

    def cleanup_audio(self, file_path: str):
        """Elimina il file audio temporaneo."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Pulito: {file_path}")
        except Exception as e:
            logger.warning(f"Errore cleanup {file_path}: {e}")
