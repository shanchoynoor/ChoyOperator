# AIOperator - Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PyQt5 Desktop GUI                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Accounts │ │ Editor   │ │Scheduler │ │ Logs & Status    │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
└───────┼────────────┼────────────┼────────────────┼─────────────┘
        │            │            │                │
        ▼            ▼            ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Controller                      │
│                   (Orchestrates all modules)                     │
└───────┬────────────┬────────────┬────────────────┬─────────────┘
        │            │            │                │
        ▼            ▼            ▼                ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐
│  Data     │ │   LLM     │ │ Browser   │ │    Scheduler      │
│  Layer    │ │  Client   │ │ Automation│ │   (APScheduler)   │
│ (SQLite)  │ │ (Claude)  │ │ (Selenium)│ │                   │
└───────────┘ └───────────┘ └─────┬─────┘ └───────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Facebook │ │ Twitter  │ │ LinkedIn │
              │ Driver   │ │ Driver   │ │ Driver   │
              └──────────┘ └──────────┘ └──────────┘
```

---

## Component Details

### 1. GUI Layer (PyQt5)
- **MainWindow**: Application shell, menu, status bar
- **AccountManager**: Add/edit/remove social accounts
- **ContentEditor**: Post composition with LLM integration
- **SchedulerWidget**: Date/time picker, timezone
- **LogViewer**: Real-time log display

### 2. Application Controller
Central coordinator that:
- Routes GUI events to appropriate modules
- Manages application state
- Handles threading for async operations

### 3. LLM Client (Claude API)
```python
class LLMClient:
    def generate_content(prompt, platform, tone) -> str
    def generate_hashtags(content, count) -> list[str]
    def improve_draft(draft) -> str
```

### 4. Browser Automation (Selenium)
```python
class BrowserManager:
    def get_driver(browser_type) -> WebDriver
    def save_session(platform, cookies)
    def load_session(platform) -> bool

class BasePlatform(ABC):
    def login(credentials) -> bool
    def create_post(content, media) -> bool
    def schedule_post(content, datetime) -> bool
```

### 5. Data Layer (SQLite)
- **Database**: Connection pool, migrations
- **Models**: Account, ScheduledPost, Log
- **Encryption**: Fernet-based credential encryption

### 6. Scheduler (APScheduler)
- Background job execution
- Persistent job store
- Retry logic with backoff

---

## Data Flow

### Content Generation Flow
```
User Input → LLM Client → Claude API → Generated Content → Preview → Post
```

### Post Creation Flow
```
Content → Platform Driver → Selenium → Browser DOM → Social Media
```

### Scheduling Flow
```
Schedule Request → APScheduler → Job Store → Trigger → Platform Driver
```

---

## Threading Model

```
┌─────────────────┐
│   Main Thread   │  ← PyQt Event Loop (GUI)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Worker │ │ Worker │  ← QThreadPool (Automation Tasks)
│ Thread │ │ Thread │
└────────┘ └────────┘
```

- GUI runs on main thread
- Automation tasks run in worker threads
- Signals/slots for thread-safe communication

---

## Security Architecture

```
┌─────────────────────────────────────┐
│           User Credentials          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Fernet Encryption (AES-128)      │
│    Key derived from master password │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      SQLite (encrypted blob)        │
└─────────────────────────────────────┘
```

API keys stored in:
- `.env` file (development)
- Windows Credential Manager (production)
