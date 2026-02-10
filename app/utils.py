import hashlib


def hash_string(
    input_string: str,
    *,
    incensitive: bool = True,
    strip: bool = True,
) -> str:
    if strip:
        input_string = input_string.strip()
    if incensitive:
        input_string = input_string.lower()
    return hashlib.blake2b(input_string.encode(), usedforsecurity=False).hexdigest()
