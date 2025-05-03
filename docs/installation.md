# Installation Guide

This guide provides detailed instructions for installing the EasyVid Transcription application on different platforms.

## Prerequisites

EasyVid requires the following software to be installed on your system:

- **Python 3.9+** - The application is built with Python and requires version 3.9 or newer
- **FFmpeg** - Required for audio extraction from video files
- **pip** - Python package installer
- **Git** - For cloning the repository and installing EZ Clip

## System Requirements

- **CPU**: A multi-core CPU is recommended (4+ cores for better performance)
- **RAM**: Minimum 8GB, 16GB or more recommended for large files
- **Storage**: At least 10GB free space (models will be downloaded and cached)
- **GPU**: Optional but recommended for faster processing:
  - NVIDIA GPU with CUDA support for significantly faster processing
  - At least 4GB VRAM for medium models, 8GB+ for large models

## Installation Steps

### 1. Install Python

#### Windows
1. Download the latest Python installer from the [official website](https://www.python.org/downloads/)
2. Run the installer and make sure to check "Add Python to PATH"
3. Verify installation by opening a command prompt and typing:
   ```
   python --version
   ```

#### macOS
1. Using Homebrew (recommended):
   ```bash
   brew install python
   ```
2. Or download from the [official website](https://www.python.org/downloads/macos/)
3. Verify installation:
   ```bash
   python3 --version
   ```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

### 2. Install FFmpeg

#### Windows
1. Download a static build from [FFmpeg Builds](https://ffmpeg.org/download.html#build-windows)
2. Extract the archive to a folder (e.g., `C:\ffmpeg`)
3. Add the `bin` folder to your system PATH
4. Verify installation:
   ```
   ffmpeg -version
   ```

#### macOS
```bash
brew install ffmpeg
ffmpeg -version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
ffmpeg -version
```

### 3. Install EasyVid

1. Clone the repository:
   ```bash
   git clone https://github.com/username/easy-vid.git
   cd easy-vid
   ```

2. (Optional but recommended) Create a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install requirements:
   ```bash
   pip install -r ez_clip_app/requirements.txt
   ```

   This will install:
   - WhisperX from GitHub
   - PyTorch (CPU version by default)
   - PyAnnote Audio for speaker diarization
   - PySide6 for the GUI
   - Other dependencies

4. (Optional) Install CUDA version of PyTorch for GPU acceleration:
   ```bash
   # For CUDA 11.8
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### 4. Hugging Face Token Setup

Speaker diarization requires a Hugging Face token to download the necessary models:

1. Create a Hugging Face account at [https://huggingface.co/join](https://huggingface.co/join)
2. Generate a token at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. Create a `.env` file in the project root:
   ```bash
   echo "HF_TOKEN=your_token_here" > .env
   ```
   
   Alternatively, set it as an environment variable:
   ```bash
   # Windows
   set HF_TOKEN=your_token_here
   
   # macOS/Linux
   export HF_TOKEN=your_token_here
   ```

## Running the Application

1. Ensure you're in the project directory (and virtual environment is activated if you created one)

2. Launch the application:
   ```bash
   python -m ez_clip_app.main
   ```

3. For verbose logging (useful for debugging):
   ```bash
   python -m ez_clip_app.main -v
   ```

## First-Run Experience

When you first run the application:

1. It will create a database file at `~/.ez_clip_app/transcripts.db`
2. The first time you transcribe a file, it will download the necessary models which may take some time depending on your internet connection
3. Models are cached for future use

## Troubleshooting

### Common Issues

#### "FFmpeg not found"
- Ensure FFmpeg is properly installed and in your system PATH
- Restart your terminal/command prompt after installation

#### PyTorch CUDA errors
- Verify your NVIDIA drivers are up-to-date
- Ensure you installed the correct PyTorch version for your CUDA version
- Check CUDA installation with:
  ```bash
  python -c "import torch; print(torch.cuda.is_available())"
  ```

#### Diarization model errors
- Verify your Hugging Face token is valid and properly set
- Check your internet connection

#### GUI not launching
- Ensure PySide6 is properly installed
- Try reinstalling:
  ```bash
  pip uninstall pyside6
  pip install pyside6
  ```

### Getting Help

If you encounter issues not covered here:

1. Check the application logs at `~/.ez_clip_app.log`
2. Open an issue on GitHub with your log file and a description of the problem
3. Check existing issues for similar problems and solutions

## Updating

To update to the latest version:

```bash
cd easy-vid
git pull
pip install -r ez_clip_app/requirements.txt
```

## Uninstallation

1. Remove the application directory:
   ```bash
   rm -rf /path/to/easy-vid
   ```

2. (Optional) Remove the database and model cache:
   ```bash
   rm -rf ~/.ez_clip_app
   rm -rf ~/.cache/torch
   rm -rf ~/.cache/huggingface
   ```