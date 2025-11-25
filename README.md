# 🎬 Reddit Video Agent - AI-Powered Viral Video Generator

Transform Reddit posts into **professional, engaging short-form videos** automatically using AI.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 🌟 Features

### Core Capabilities
- 🤖 **Fully Automated Pipeline**: From Reddit URL to finished video in minutes
- 🎙️ **AI Voiceover**: Natural-sounding narration using Google TTS
- 🎨 **Context-Aware Visuals**: AI-generated images that match narration content
- 📸 **Reddit Screenshots**: Automatic capture of posts and comments
- 🎵 **Professional Audio Mixing**: Advanced ducking (90% → 30% during overlap)
- 📝 **Synchronized Captions**: Tempo-aware subtitle synchronization
- 🎬 **Multi-Track Timeline**: Beat-synchronized composition

### V2 Architecture (Latest)
- **AssetManagerAgent**: Intelligent asset organization & validation
- **CompositionStrategyAgent**: Content-aware strategy selection
- **TimelineArchitectAgent**: Professional multi-track timeline builder
- **EditorAgent**: Advanced rendering with Z-index layering

### Advanced Features
- ✅ **Factual vs Ambiguous Visual Markers**: Expectation management in narration
- ✅ **Z-Index Layering**: Guaranteed correct asset visibility
- ✅ **Audio Ducking**: 90% base volume, 30% during narration overlap
- ✅ **Caption Sync**: Tempo-adjusted timing for perfect synchronization
- ✅ **Context-Aware Images**: Generated based on script markers

## 📋 Prerequisites

- **Python 3.9+**
- **FFmpeg** (for video processing)
- **Chrome/Chromium** (for screenshot capture)
- **Google Gemini API Key** (for AI generation)
- **ImageMagick** (optional, for advanced text rendering)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/reddit-video-agent.git
cd reddit-video-agent
```

### 2. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Install FFmpeg (Windows)
# Download from https://ffmpeg.org/download.html
```

### 3. Configure API Keys
Create `.env` file in project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY_2=your_backup_key_here  # Optional
GEMINI_API_KEY_3=your_backup_key_here  # Optional
```

Get your Gemini API key from: https://ai.google.dev/

### 4. Run
```bash
python3 -m reddit_video_agent.main "https://www.reddit.com/r/nextfuckinglevel/comments/..."
```

## 📖 Usage

### Basic Usage
```bash
python3 -m reddit_video_agent.main <reddit_url>
```

### Example
```bash
python3 -m reddit_video_agent.main "https://www.reddit.com/r/nextfuckinglevel/comments/1p38jk1/float_like_a_butterfly_sting_like_a_bee/"
```

### Output
Video will be saved to: `reddit_video_agent/output/final_video.mp4`

## 🏗️ Architecture

### Pipeline Flow
```
1. Scraping       → Reddit post + comments + video
2. Scripting      → AI-generated narration with markers
3. Audio          → TTS + Whisper transcription
4. Visuals        → AI images + screenshots
5. Asset Mgmt     → Organization + validation
6. Strategy       → Composition strategy selection
7. Timeline       → Beat-synchronized multi-track
8. Rendering      → Final video with Z-index layering
```

### V2 Agent System
```
Director
├── ScraperAgent
├── ScriptwriterAgent (with visual markers)
├── VoiceoverAgent
├── AudioAgent (Whisper)
├── VisualAgent (context-aware)
├── ClipperAgent
├── AssetManagerAgent ✨
├── CompositionStrategyAgent ✨
├── TimelineArchitectAgent ✨
└── EditorAgent (Z-index renderer) ✨
```

## 🎨 Visual Markers System

### SHOW Markers (Screenshots)
```
*<SHOW:screenshot_post>* - Reddit post screenshot
*<SHOW:screenshot_comment_1>* - Comment screenshot
```

### VISUAL Markers (AI-Generated)
```
Factual: *<VISUAL:factual|spinning_bar|boxing training equipment>*
Ambiguous: *<VISUAL:ambiguous|mohawk|gangster mohawk hairstyle>*
```

## ⚙️ Configuration

Edit `reddit_video_agent/core/config.py`:

```python
class Config:
    # Resolution
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920  # 9:16 for TikTok/Shorts
    
    # Models
    SCRIPT_MODEL = "gemini-2.0-flash-exp"
    WHISPER_MODEL = "base"
    
    # Audio
    TTS_VOICE = "id-ID-Standard-D"  # Indonesian male
    
    # Timing
    DEFAULT_TEMPO = 1.1  # 10% faster
```

## 🐛 Troubleshooting

### Common Issues

**1. "Module 'importlib.metadata' error"**
```bash
pip install --upgrade importlib-metadata
```

**2. "FFmpeg not found"**
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

**3. "Quota exceeded" (Gemini API)**
- Add multiple API keys in `.env`
- Wait for quota reset (free tier: 15 requests/minute)

**4. "ImageMagick not found" (Caption errors)**
```bash
# macOS
brew install imagemagick

# Ubuntu
sudo apt-get install imagemagick
```

**5. "rembg background removal fails"**
- Requires ~2GB RAM
- First run downloads AI model (~200MB)

## 📊 Performance

- **Processing Time**: 3-5 minutes per video (depends on length)
- **Memory Usage**: ~2-4GB RAM
- **Disk Space**: ~500MB for models + generated assets

## 🔮 Future Enhancements

See `FUTURE_ENHANCEMENTS.md` for planned features:
- TikTok-style word highlighting
- Advanced transitions & effects
- Multi-language support
- Batch processing

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see `LICENSE` file for details

## 🙏 Acknowledgments

- **Google Gemini** - AI generation
- **OpenAI Whisper** - Speech recognition
- **MoviePy** - Video editing
- **rembg** - Background removal

## 📧 Contact

- GitHub Issues: [Report bugs](https://github.com/yourusername/reddit-video-agent/issues)
- Reddit: [r/AutomatedVideoCreation](https://reddit.com/r/AutomatedVideoCreation)

## ⭐ Star History

If you find this project useful, please give it a star! ⭐

---

**Made with ❤️ for the Reddit community**
