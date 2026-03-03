from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class State:
    last_time_ms: int = 0

class JsonStateStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> State:
        if not self.path.exists():
            return State(last_time_ms=0)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return State(last_time_ms=int(data.get("last_time_ms", 0)))

    def save(self, state: State) -> None:
        self.path.write_text(
            json.dumps({"last_time_ms": state.last_time_ms}, indent=2),
            encoding="utf-8",
        )