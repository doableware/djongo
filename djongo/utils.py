def encode_key(s: str):
    return s.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def encode_keys(obj, is_key=False):
    if isinstance(obj, dict):
        return {encode_keys(k, True): encode_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [encode_keys(v) for v in obj]
    if isinstance(obj, int) and is_key:
        return str(obj)
    if isinstance(obj, str) and is_key:
        return encode_key(obj)
    return obj


def decode_key(s: str):
    return s.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")


def decode_keys(obj, is_key=False):
    if isinstance(obj, dict):
        return {decode_keys(k, True): decode_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decode_keys(v) for v in obj]
    if isinstance(obj, str) and is_key and (obj.isdigit() or (obj.startswith('-') and obj[1:].isdigit())):
        return int(obj)
    if isinstance(obj, str) and is_key:
        return decode_key(obj)
    return obj
