import json
import os
from pathlib import Path

APP_NAME = "AmigurumiAI"


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData/Roaming"))
    elif os.sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def save_config(data: dict) -> None:
    path = config_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    if os.name != "nt":
        try:
            path.chmod(0o600)
        except OSError:
            pass


def get_api_key() -> str:
    return os.getenv("OPENAI_API_KEY") or str(load_config().get("openai_api_key", ""))


def set_api_key(value: str) -> None:
    data = load_config()
    if value.strip():
        data["openai_api_key"] = value.strip()
    else:
        data.pop("openai_api_key", None)
    save_config(data)
