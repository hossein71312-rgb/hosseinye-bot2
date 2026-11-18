import json
from pathlib import Path

STATE_FILE = Path("database/published.json")

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    state.setdefault("published", [])
    return state

def done(state, key):
    return key in state["published"]

def mark(state, key):
    if key not in state["published"]:
        state["published"].append(key)
    state["published"] = state["published"][-300:]

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
