# EZ CLIP Transcription

<div align="center">

*A desktop application for high-accuracy video/audio transcription with speaker diarization*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/kingbootoshi/ez-clip)](https://github.com/kingbootoshi/ez-clip/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/kingbootoshi/ez-clip/pulls)

</div>

## ✨ Features

- **High-quality transcription** using WhisperX with word-level timestamps
- **Speaker diarization** to identify who said what
- **Desktop GUI** for easy interaction and real-time progress tracking
- **SQLite database** storage for transcripts and speaker segments
- **Cross-platform** support for macOS, Windows, and Linux
- **Future-proof architecture** ready to be used in web applications

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/username/easy-vid.git
cd easy-vid

# Install dependencies
pip install -r ez_clip_app/requirements.txt

# Run the application
python -m ez_clip_app.main
```

### Requirements

- Python 3.9+
- PyTorch (CPU or CUDA)
- FFmpeg
- A Hugging Face token for speaker diarization functionality

For detailed installation instructions, see our [Installation Guide](docs/installation.md).

## 🖥️ Usage

1. **Launch the application**
   ```bash
   python -m ez_clip_app_app.main
   ```

2. **Select a media file**
   Click "Select Media File" button to choose your video or audio file

3. **Configure transcription settings**
   - Choose model size (tiny, base, small, medium, large-v1, large-v2)
   - Set language or use auto-detection
   - Enable/disable speaker diarization
   - Configure number of speakers

4. **View results**
   - Full transcript in the "Full Transcript" tab
   - Speaker-separated segments in the "Segments" tab

5. **Data is stored in SQLite**
   Database is stored at `~/.ez_clip_app/transcripts.db`

## 📖 Documentation

Comprehensive documentation is available in the [docs directory](docs/):

- [Installation Guide](docs/installation.md)
- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Database Schema](docs/database.md)
- [Extending the Application](docs/extending.md)
- [Contributing Guide](docs/contributing.md)

## 🧪 Technical Details

EZ Clip uses state-of-the-art speech processing libraries:

- **WhisperX**: Enhanced version of OpenAI's Whisper with improved alignment
- **PyAnnote**: For speaker diarization
- **PySide6**: For cross-platform GUI
- **SQLite**: For efficient local data storage

The application is designed with modularity in mind, making it easy to extend or integrate into other services.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For more details, see our [Contributing Guide](docs/contributing.md).

## 🙏 Acknowledgements

- [WhisperX](https://github.com/m-bain/whisperX) - Enhanced Whisper with word-level timestamps
- [PyAnnote Audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [OpenAI](https://openai.com) - Original Whisper ASR system
- [FFmpeg](https://ffmpeg.org) - Audio extraction and processing

---

<div align="center">
  <sub>Built with ❤️ by [Your Name/Organization]</sub>
</div>