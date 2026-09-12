import os

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
TRACE_SENSITIVE_DATA = os.getenv("TRACE_SENSITIVE_DATA", "false").lower() in {
    "1", "true", "yes"
}
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", "200000"))
MAX_TOTAL_BYTES = int(os.getenv("MAX_TOTAL_BYTES", "2000000"))
MAX_FILES = int(os.getenv("MAX_FILES", "80"))
MAX_CHARS_PER_FILE = int(os.getenv("MAX_CHARS_PER_FILE", "30000"))
ALLOWED_EXTENSIONS = {
    ".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json",
}
