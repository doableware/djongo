def encode_keys(obj, is_key=False):
    if isinstance(obj, dict):
        return {encode_keys(k, True): encode_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [encode_keys(v) for v in obj]
    if isinstance(obj, str) and is_key:
        return obj.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")
    return obj

def decode_keys(obj, is_key=False):
    if isinstance(obj, dict):
        return {decode_keys(k, True): decode_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decode_keys(v) for v in obj]
    if isinstance(obj, str) and is_key:
        return obj.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")
    return obj