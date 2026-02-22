import logging

from app import models, schemas, services


class AuthController:
    def __init__(
        self,
        user_service: services.UserService,
        auth_service: services.AuthService,
    ):
        self.__logger = logging.getLogger(__name__)
        self.__user_service = user_service
        self.__auth_service = auth_service

    def login(self, email: str, password: str) -> models.User | None:
        self.__logger.info(f"Login attempt for: {email}")
        user = self.__user_service.authenticate(email, password)
        if user:
            self.__logger.info(f"Login successful for: {email} (role={user.role})")
        else:
            self.__logger.warning(f"Login failed for: {email}")
        return user

    def register(
        self,
        name: str,
        email: str,
        password: str,
        role: str,
    ) -> models.User:
        self.__logger.info(f"Registration attempt: {email} as {role}")
        create_schema = schemas.CreateUser(
            name=name,
            email=email,
            password=password,
            role=role,
        )
        user = self.__user_service.create_user(create_schema)
        self.__logger.info(f"Registration successful: {email}")
        return user
