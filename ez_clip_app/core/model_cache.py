"""
Singleton model loaders for WhisperX and PyAnnote.
"""
import torch
import logging
from ez_clip_app.config import DEFAULT_MODEL_SIZE, DEVICE, HF_TOKEN

# Set up logging
logger = logging.getLogger(__name__)

# Cache for loaded models
_WHISPER_MODELS = {}
_DIARIZATION_MODELS = {}

def get_whisper(model_size=DEFAULT_MODEL_SIZE):
    """Get or load WhisperX model.
    
    Args:
        model_size: Model size ('tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2')
        
    Returns:
        Loaded WhisperX model
    """
    if model_size not in _WHISPER_MODELS:
        try:
            import whisperx
            logger.info(f"Loading WhisperX {model_size} model...")
            
            # Use CUDA if available, otherwise use CPU
            device = DEVICE
            compute_type = "float16" if device == "cuda" else "float32"
            
            # Load the model
            _WHISPER_MODELS[model_size] = whisperx.load_model(
                model_size, 
                device=device,
                compute_type=compute_type
            )
            logger.info(f"WhisperX {model_size} model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading WhisperX model: {e}")
            raise
    
    return _WHISPER_MODELS[model_size]

def get_diarization_model():
    """Get or load PyAnnote diarization model.
    
    Returns:
        Loaded diarization pipeline
    """
    if not _DIARIZATION_MODELS.get("diarize"):
        try:
            from pyannote.audio import Pipeline
            
            if not HF_TOKEN:
                logger.warning("No HuggingFace token found. Speaker diarization might not work.")
            
            logger.info("Loading diarization model...")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=HF_TOKEN
            )
            
            # Move to appropriate device
            if DEVICE == "cuda" and torch.cuda.is_available():
                pipeline = pipeline.to(torch.device("cuda"))
            
            _DIARIZATION_MODELS["diarize"] = pipeline
            logger.info("Diarization model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading diarization model: {e}")
            raise
    
    return _DIARIZATION_MODELS["diarize"]

def get_alignment_model():
    """Get or load WhisperX alignment model.
    
    Returns:
        Loaded alignment model
    """
    if not _DIARIZATION_MODELS.get("align"):
        try:
            import whisperx
            
            logger.info("Loading alignment model...")
            model_a, metadata = whisperx.load_align_model(
                language_code="en",
                device=DEVICE
            )
            _DIARIZATION_MODELS["align"] = (model_a, metadata)
            logger.info("Alignment model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading alignment model: {e}")
            raise
    
    return _DIARIZATION_MODELS["align"]