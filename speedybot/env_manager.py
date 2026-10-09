import os


def find_env_file():
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        "/root/SpeedyBot/.env",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, ".env")


def load_env_file(path=None):
    if path is None:
        path = find_env_file()
    if not path or not os.path.isfile(path):
        return {}
    loaded = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                    val = val[1:-1]
                loaded[key] = val
                if key and key not in os.environ:
                    os.environ[key] = val
    return loaded


def update_env_file(updates: dict, path=None):
    if path is None:
        path = find_env_file()
    lines = []
    found_keys = set()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

    has_export = any(l.strip().startswith("export ") for l in lines)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        is_export = stripped.startswith("export ")
        content = stripped[7:].strip() if is_export else stripped
        if content and not content.startswith("#") and "=" in content:
            key = content.split("=", 1)[0].strip()
            if key in updates:
                found_keys.add(key)
                val = updates[key]
                prefix = "export " if (is_export or has_export or not lines) else ""
                escaped_val = str(val).replace("'", "'\\''")
                new_lines.append(f"{prefix}{key}='{escaped_val}'\n")
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in found_keys:
            prefix = "export " if (has_export or not lines) else ""
            escaped_val = str(val).replace("'", "'\\''")
            new_lines.append(f"{prefix}{key}='{escaped_val}'\n")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
