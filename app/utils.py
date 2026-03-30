from datetime import datetime, timezone
import hashlib

from uuid_utils import uuid4


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


def uuid4_hex() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
