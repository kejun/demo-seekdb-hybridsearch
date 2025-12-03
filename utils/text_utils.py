import re
import json
import math
import pandas as pd


def sanitize_text(text):
    if text is None or pd.isna(text):
        return ""

    text_str = str(text)
    text_str = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text_str)
    text_str = re.sub(r'[ \t]+', ' ', text_str)
    text_str = re.sub(r'\n\s*\n', '\n', text_str)
    text_str = text_str.encode('utf-8', errors='ignore').decode('utf-8')
    return text_str.strip()


def ensure_json_safe(obj):
    if isinstance(obj, dict):
        return {ensure_json_safe(str(k)): ensure_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_safe(item) for item in obj]
    elif isinstance(obj, str):
        cleaned = sanitize_text(obj)
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        if '"' in cleaned or '"' in cleaned or '"' in cleaned:
            cleaned = cleaned.replace('"', "'").replace('"', "'").replace('"', "'")
        try:
            json.dumps(cleaned, ensure_ascii=False)
            return cleaned
        except Exception:
            return ""
    elif isinstance(obj, (int, float)):
        if isinstance(obj, float) and not math.isfinite(obj):
            return 0.0
        return obj
    elif isinstance(obj, bool):
        return obj
    elif obj is None:
        return None
    else:
        try:
            return ensure_json_safe(str(obj))
        except Exception:
            return ""

