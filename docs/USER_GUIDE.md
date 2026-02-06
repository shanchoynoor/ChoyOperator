# AIOperator User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Adding Accounts](#adding-accounts)
3. [Creating Posts](#creating-posts)
4. [Scheduling Posts](#scheduling-posts)
5. [Drag & Drop Scheduling](#drag--drop-scheduling)
6. [Folder Watching](#folder-watching)
7. [Settings](#settings)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Time Setup

1. **Launch AIOperator** from your Start Menu or desktop shortcut.

2. **Configure API Key**:
   - Go to **File → Settings → API**
   - Enter your OpenRouter API key
   - Click **Save**

3. **Add an Account**:
   - Click **+ Add** in the left sidebar
   - Select platform and enter credentials
   - Click **Add Account**

### Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  File   View   Help                                     │
├────────────┬────────────────────────────┬───────────────┤
│            │                            │               │
│  Accounts  │     Content Editor         │    Logs       │
│            │                            │               │
│  📘 FB     │  ┌──────────────────────┐  │  ℹ️ Ready    │
│  🐦 Twitter│  │ Write your post...   │  │  ℹ️ Started  │
│            │  └──────────────────────┘  │               │
│            │                            │               │
│  + Add     │  🤖 Generate  ✨ Improve   │               │
│  Remove    │                            │               │
│            ├────────────────────────────┤               │
│            │  📅 Scheduled Posts        │               │
│            │  [Drop files here]         │               │
│            │                            │               │
└────────────┴────────────────────────────┴───────────────┘
```

---

## Adding Accounts

1. Click **+ Add** in the Accounts panel
2. Select the platform:
   - Facebook
   - Twitter/X
   - LinkedIn
   - YouTube
3. Enter your login credentials
4. Click **Add Account**

> **Note**: Credentials are encrypted before storage using AES encryption.

---

## Creating Posts

### Manual Writing

1. Select an account from the sidebar
2. Type your content in the editor
3. Use the character counter to stay within limits
4. Click **📤 Post Now** to publish

### AI-Assisted Content

1. Enter a topic in the "Topic" field
2. Select **Tone** (Professional, Casual, Engaging, etc.)
3. Select target **Platform**
4. Click **🤖 Generate** to create content

### AI Features

| Button | Function |
|--------|----------|
| 🤖 Generate | Create new post from topic |
| ✨ Improve | Enhance existing content |
| #️⃣ Add Hashtags | Generate relevant hashtags |

---

## Scheduling Posts

### Schedule from Editor

1. Create your content
2. Click the calendar icon or schedule menu
3. Select date and time
4. Click **📅 Schedule Post**

### View Scheduled Posts

- All scheduled posts appear in the **Scheduled Posts** table
- Status shows: Pending, Running, Completed, or Failed
- Click **Cancel Selected** to remove scheduled posts

---

## Drag & Drop Scheduling

The quickest way to schedule media posts:

1. **Drag files** (images/videos) onto the drop zone
2. **AI generates** title, description, and hashtags
3. **Set schedule time** using the date picker
4. **Click Schedule** to confirm

Supported formats:
- Images: JPG, PNG, GIF, WebP
- Videos: MP4, MOV, AVI

---

## Folder Watching

Automatically schedule posts from a folder:

### Setup

1. Go to **File → Settings → Folder Watch**
2. Enable **📂 Watch Folder**
3. Click **Browse** and select a folder
4. Configure options:
   - **Auto-generate content**: Let AI create descriptions
   - **Default delay**: Time before posting (e.g., 1 hour)

### Usage

Simply add files to your watched folder. AIOperator will:
1. Detect new files automatically
2. Open the schedule dialog
3. Generate AI content (if enabled)
4. Add to schedule queue

---

## Settings

Access via **File → Settings**

### API Tab
- **OpenRouter API Key**: Required for AI features
- **LLM Model**: Choose Claude version

### Browser Tab
- **Browser**: Chrome or Firefox
- **Headless**: Run browser in background
- **Timeout**: Page load timeout

### Folder Watch Tab
- **Watch Folder**: Path to monitor
- **Auto-generate**: Enable AI content
- **Default delay**: Scheduling delay

### General Tab
- **Log Level**: DEBUG, INFO, WARNING, ERROR
- **Start minimized**: Launch to system tray

---

## Troubleshooting

### Common Issues

**"LLM Not Configured"**
- Add your OpenRouter API key in Settings → API

**"No Account Selected"**
- Click an account in the sidebar before posting

**"Content exceeds limit"**
- Check the character counter
- Shorten content or use AI to rewrite

**Browser not opening**
- Install Chrome or Firefox
- Check Settings → Browser configuration

**Posts failing**
- Check Logs panel for error details
- Platform may have changed UI elements
- Try logging in manually first

### Getting Help

1. Check the Logs panel for detailed error messages
2. Generate error report: **Help → Generate Error Report**
3. Review `logs/errors.log` for full history

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+, | Open Settings |
| F5 | Refresh all data |
| Ctrl+Enter | Post Now |
| Alt+F4 | Exit |

---

## Platform-Specific Notes

### Facebook
- Uses Facebook web interface
- Session cookies saved for faster logins

### Twitter/X
- Supports text and media tweets
- 280 character limit enforced

### LinkedIn
- Professional tone recommended
- 3000 character limit

### YouTube
- Supports community posts and video uploads
- Video uploads may take time depending on file size
