# AIOperator

Windows Desktop Automation with LLM & Browser DOM for Social Media Management.

## Features

- **AI-Powered Content Generation** - Generate posts, captions, descriptions, and hashtags using Claude via OpenRouter
- **Multi-Platform Support** - Facebook, Twitter/X, LinkedIn, and YouTube
- **Drag & Drop Scheduling** - OBS-style file drop with AI-generated content
- **Folder Watching** - Auto-schedule posts from a watched directory
- **Encrypted Credentials** - Secure storage using Fernet (AES) encryption
- **Background Scheduler** - APScheduler with SQLite persistence
- **Dark Theme UI** - Modern PyQt5 desktop application

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your OpenRouter API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Run the Application

```bash
python run.py
```

## Project Structure

```
AIOperator/
├── src/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── core/
│   │   ├── llm_client.py    # OpenRouter/Claude integration
│   │   ├── browser_automation.py  # Selenium WebDriver
│   │   ├── scheduler.py     # APScheduler management
│   │   └── platforms/       # Platform-specific drivers
│   │       ├── facebook.py
│   │       ├── twitter.py
│   │       ├── linkedin.py
│   │       └── youtube.py
│   ├── data/
│   │   ├── database.py      # SQLite operations
│   │   ├── models.py        # Data models
│   │   └── encryption.py    # Credential encryption
│   ├── gui/
│   │   ├── main_window.py   # Main application window
│   │   └── widgets/         # UI components
│   └── utils/
│       ├── logger.py        # Logging configuration
│       └── helpers.py       # Utility functions
├── data/                    # SQLite DB, cookies, screenshots
├── logs/                    # Application logs
├── docs/                    # Documentation
├── requirements.txt
├── .env.example
└── run.py
```

## Requirements

- Python 3.11+
- Chrome or Firefox browser
- OpenRouter API key (for Claude access)

## Tech Stack

| Component | Technology |
|-----------|------------|
| GUI | PyQt5 |
| LLM | Claude via OpenRouter API |
| Browser Automation | Selenium WebDriver |
| Scheduler | APScheduler |
| Database | SQLite |
| Encryption | Fernet (cryptography) |

## Usage

### Adding Accounts
1. Click **+ Add** in the Accounts panel
2. Select platform and enter credentials
3. Credentials are encrypted before storage

### Creating Posts
1. Write content or use AI generation
2. Select tone and platform
3. Click **🤖 Generate** for AI content
4. Click **📤 Post Now** or schedule

### Scheduling with Drag & Drop
1. Drag media files to the drop zone
2. AI generates title/description
3. Set schedule time
4. Click **📅 Schedule Post**

### Folder Watching
1. Go to **File > Settings > Folder Watch**
2. Enable and select a folder
3. New files are auto-detected for scheduling

## Security Notes

- API keys stored in `.env` (not committed)
- Credentials encrypted with Fernet (AES)
- Sessions saved as cookies for fewer logins
- Browser runs in visible mode by default

## License

MIT License
