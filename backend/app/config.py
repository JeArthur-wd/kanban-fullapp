import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

# OpenRouter configuration
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0"))

# Sign-in. The MVP has one account; override with PM_LOGIN_USER / PM_LOGIN_PASSWORD.
DEFAULT_LOGIN_USER = "user"
DEFAULT_LOGIN_PASSWORD = "password"
SESSION_TTL_SECONDS = 7 * 24 * 3600
# Without PM_SESSION_SECRET a random key is made per process, so sessions end on restart.
_FALLBACK_SESSION_SECRET = secrets.token_hex(32)

# AI chat limits
CHAT_MESSAGE_MAX_CHARS = 4000
CHAT_HISTORY_MAX_ITEMS = 20
CHAT_RATE_LIMIT = 20  # requests per minute
LOGIN_RATE_LIMIT = 10  # attempts per minute

# Database configuration
DEFAULT_BOARD_TITLE = "My Board"

# Initial seed data for new boards
INITIAL_COLUMNS = [
    ("Backlog", [
        ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
        ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ]),
    ("Discovery", [
        ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ]),
    ("In Progress", [
        ("Refine status language", "Standardize column labels and tone across the board."),
        ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ]),
    ("Review", [
        ("QA micro-interactions", "Verify hover, focus, and loading states."),
    ]),
    ("Done", [
        ("Ship marketing page", "Final copy approved and asset pack delivered."),
        ("Close onboarding sprint", "Document release notes and share internally."),
    ]),
]


def get_db_path() -> Path:
    env_path = os.getenv("PM_DB_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "data" / "pm.db"


def resolve_static_dir() -> Path | None:
    env_dir = os.getenv("PM_STATIC_DIR", "").strip()
    candidates = [
        Path(env_dir) if env_dir else None,
        Path(__file__).resolve().parents[2] / "frontend" / "out",
        Path("/app/frontend/out"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def get_openrouter_api_key() -> str | None:
    return os.getenv("OPENROUTER_API_KEY")


def get_login_credentials() -> tuple[str, str]:
    return (
        os.getenv("PM_LOGIN_USER") or DEFAULT_LOGIN_USER,
        os.getenv("PM_LOGIN_PASSWORD") or DEFAULT_LOGIN_PASSWORD,
    )


def get_session_secret() -> bytes:
    return (os.getenv("PM_SESSION_SECRET") or _FALLBACK_SESSION_SECRET).encode()
