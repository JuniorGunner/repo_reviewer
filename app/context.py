from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReviewContext:
    root: Path
