# AI YouTube Generator - Copilot Instructions

## Project Overview

**ai-youtube-generator** is a Python-based pipeline that automates YouTube video creation through three distinct stages:
1. **Script Generation** - Uses OpenAI GPT-4 to generate YouTube video scripts from topics
2. **Audio Synthesis** - Converts scripts to audio using pyttsx3 (text-to-speech)
3. **Video Composition** - Assembles images with synchronized audio into MP4 videos using MoviePy

The pipeline is designed for YouTube Shorts and educational content, with initial focus on Sanatan Dharma topics.

## Architecture & Data Flow

### Stage 1: Script Generation (`scripts/generate_script.py`)
- **Input**: Topic string (e.g., "Sanatan Dharma principles")
- **Process**: Calls OpenAI GPT-4 API with system prompt: "You are a YouTube script generator"
- **Output**: Raw script text saved to `scripts/generated_scripts/{topic}.txt`
- **API Key Source**: `config/api_keys.json` (OPENAI_API_KEY environment variable)
- **Note**: Direct file API usage; no framework abstractions

### Stage 2: Audio Synthesis (`scripts/text_to_speech.py`)
- **Input**: Script text from `scripts/generated_scripts/{filename}`
- **Process**: pyttsx3 engine converts text to MP3, handles filename sanitization (spaces → underscores)
- **Output**: MP3 file to `scripts/generated_audio/{topic}.mp3`
- **Key Pattern**: Interactive CLI that prompts for topic name and script filename separately
- **Important**: Folder creation with `mkdir(exist_ok=True)` pattern used throughout

### Stage 3: Video Composition (`scripts/generate_video.py`)
- **Inputs**: 
  - Audio: `scripts/generated_audio/Sanatan_Dharma_principles.mp3` (hardcoded - needs parameterization)
  - Images: JPG/PNG files from `scripts/images/`
- **Process**: 
  - Loads images sorted alphabetically
  - Sets 3 seconds per image clip
  - Concatenates using MoviePy 2.x API
  - Syncs to audio duration
- **Output**: `scripts/final_video.mp4` at 24 fps
- **Critical Note**: Current implementation has hardcoded audio path and output name

## Key Technical Patterns & Conventions

### Path Handling
- All paths are relative to project root
- Uses `Path()` from pathlib for modern file operations
- Folder creation always uses `os.makedirs(..., exist_ok=True)` pattern
- Example: `Path("scripts/generated_audio")` convention followed consistently

### API Integration
- OpenAI API key stored in `config/api_keys.json` (should move to environment variables for security)
- Uses OpenAI Python client library with `chat.completions.create()` interface
- Model hardcoded to GPT-4 in `generate_script.py`

### MoviePy 2.x Specifics
- Import pattern: Individual imports from submodules (`from moviepy.video.io.VideoFileClip import VideoFileClip`)
- Known issue noted in code: `concatenate_videoclips` "sometimes breaks in 2.x"
- Image duration fixed at 3 seconds; audio duration drives final video length
- FPS set to 24

### Text-to-Speech
- Uses pyttsx3 (local, no API calls)
- Blocking `engine.runAndWait()` pattern
- Cross-platform support (Windows/Mac/Linux)

## Current Limitations & Improvement Points

### Script Generation (`generate_script.py`)
- No error handling for API failures
- No retry logic for rate limits
- Accepts only topic parameter; no customization of script tone/length
- No caching of generated scripts

### Audio Synthesis (`text_to_speech.py`)
- Interactive CLI only; not callable from other modules
- No voice customization (rate, pitch, volume)
- pyttsx3 has poor voice quality; consider adding ElevenLabs or Azure TTS support

### Video Composition (`generate_video.py`)
- **Hardcoded values**: Audio filename and output path must be manually edited
- Image sorting alphabetical only; no custom ordering
- No progress feedback during video rendering (can be slow)
- No error handling for missing audio/images
- Should refactor to accept parameters instead of hardcoding

### Project Structure
- `uploader/` and `utils/` folders are empty (placeholder for future YouTube upload logic)
- No configuration file for pipeline parameters
- No logging infrastructure
- Missing requirements.txt or environment specification

## Development Workflow

### Running the Pipeline
```bash
# 1. Generate script (outputs to scripts/generated_scripts/)
python scripts/generate_script.py

# 2. Generate audio (interactive - prompts for topic/script filename)
python scripts/text_to_speech.py

# 3. Compose video (requires images in scripts/images/)
python scripts/generate_video.py
```

### Setup Requirements
- Python 3.8+
- Dependencies: `openai`, `pyttsx3`, `moviepy`, `imageio-ffmpeg`
- OpenAI API key in `config/api_keys.json` or OPENAI_API_KEY environment variable
- Generated script text files in `scripts/generated_scripts/`
- Image files (JPG/PNG) in `scripts/images/`

### Testing Points
- Verify API key access before running script generation
- Check MoviePy/FFmpeg availability before video composition
- Ensure image folder has properly formatted files before video generation

## Common Tasks for AI Agents

### Adding a New Generation Step
- Follow the existing pattern: input folder → processing → output folder
- Use `Path()` and `mkdir(exist_ok=True)` for file operations
- Place in `scripts/` directory
- Integrate with existing generated scripts/audio/images flow

### Refactoring to Remove Hardcoding
- Priority: `generate_video.py` (audio_file and output_file hardcoded)
- Convert to function parameters with sensible defaults
- Consider central configuration file in `config/` for all paths

### Adding Error Handling
- OpenAI API: Add try-except with exponential backoff for rate limits
- File operations: Validate paths exist before processing
- MoviePy: Check for FFmpeg availability and missing media files

### Future Enhancement Points
- Parameterize all hardcoded values → refactor `generate_video.py`
- Add logging throughout pipeline
- Create `uploader/` logic for YouTube upload integration
- Implement configuration file for pipeline parameters
- Consider async processing for video composition (currently blocking)

## File Structure Reference

```
scripts/
├── generate_script.py     # OpenAI script generation
├── text_to_speech.py      # pyttsx3 audio synthesis
├── generate_video.py      # MoviePy video composition
├── generated_scripts/     # Output: Script text files
├── generated_audio/       # Output: MP3 audio files
└── images/               # Input: Image files for video

config/
└── api_keys.json         # API credentials (move to env vars)

uploader/                 # Placeholder: YouTube upload logic
utils/                    # Placeholder: Utility functions
```
