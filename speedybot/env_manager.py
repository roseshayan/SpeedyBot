import os
import re
import shlex
import tempfile
import threading


_ENV_LOCK = threading.RLock()
_ENV_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _decode_ansi_c_value(value):
    """Decode legacy Bash ``printf %q`` values without running a shell.

    Octal and hexadecimal escapes represent UTF-8 bytes; Unicode escapes
    represent code points. Leave malformed/non-UTF-8 values intact.
    """
    if len(value) < 3 or not value.endswith("'"):
        return value
    content = value[2:-1]
    decoded = bytearray()
    escapes = {
        "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f",
        "n": "\n", "r": "\r", "t": "\t", "v": "\v",
        "\\": "\\", "'": "'", '"': '"', "?": "?",
    }
    index = 0
    try:
        while index < len(content):
            char = content[index]
            index += 1
            if char == "'":
                raise ValueError("Unescaped quote")
            if char != "\\":
                decoded.extend(char.encode("utf-8"))
                continue
            if index == len(content):
                raise ValueError("Incomplete escape")
            escape = content[index]
            index += 1
            if escape in escapes:
                decoded.extend(escapes[escape].encode("utf-8"))
            elif escape in "01234567":
                start = index - 1
                while index < len(content) and index - start < 3 and content[index] in "01234567":
                    index += 1
                decoded.append(int(content[start:index], 8) & 255)
            elif escape in "xuU":
                start = index
                limit = {"x": 2, "u": 4, "U": 8}[escape]
                while index < len(content) and index - start < limit and content[index] in "0123456789abcdefABCDEF":
                    index += 1
                if index == start:
                    raise ValueError("Incomplete numeric escape")
                code = int(content[start:index], 16)
                if escape == "x":
                    decoded.append(code)
                else:
                    decoded.extend(chr(code).encode("utf-8"))
            elif escape == "c":
                if index == len(content) or ord(content[index]) > 127:
                    raise ValueError("Invalid control escape")
                control = content[index]
                index += 1
                decoded.append(127 if control == "?" else ord(control.upper()) & 31)
            else:
                # Bash preserves the backslash for unrecognized escapes.
                decoded.extend(("\\" + escape).encode("utf-8"))
        result = decoded.decode("utf-8")
        if "\x00" in result:
            raise ValueError("NUL cannot appear in an environment value")
        return result
    except (ValueError, UnicodeError):
        return value


def _decode_value(value):
    """Decode shell quoting without executing expansions or shell commands."""
    if value.startswith("$'"):
        return _decode_ansi_c_value(value)
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return " ".join(lexer)
    except ValueError:
        return value


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
                if not _ENV_KEY.fullmatch(key):
                    continue
                val = _decode_value(val)
                loaded[key] = val
                if key and key not in os.environ:
                    os.environ[key] = val
    return loaded


def update_env_file(updates: dict, path=None):
    """Write shell-safe values atomically, preserving comments and other keys."""
    normalized = {}
    for key, value in updates.items():
        if not isinstance(key, str) or not _ENV_KEY.fullmatch(key):
            raise ValueError("Invalid environment variable name")
        value = str(value)
        if any(char in value for char in ("\n", "\r", "\x00")):
            raise ValueError("Environment values must fit on one line")
        normalized[key] = value
    with _ENV_LOCK:
        _update_env_file(normalized, path)


def _update_env_file(updates: dict, path=None):
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
            if new_lines and not new_lines[-1].endswith(("\n", "\r")):
                new_lines[-1] += "\n"
            prefix = "export " if (has_export or not lines) else ""
            escaped_val = str(val).replace("'", "'\\''")
            new_lines.append(f"{prefix}{key}='{escaped_val}'\n")

    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".env-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(new_lines)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
