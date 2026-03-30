import logging

import bcrypt


class AuthService:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)

    def hash_password(self, password: str) -> str:
        self.__logger.debug("Hashing password")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.__logger.debug("Password hashed successfully")
        return hashed

    def verify_password(self, password: str, password_hash: str) -> bool:
        self.__logger.debug("Verifying password")
        is_valid = bcrypt.checkpw(password.encode(), password_hash.encode())
        self.__logger.debug(f"Password verification result: {is_valid}")
        return is_valid
