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

    def login(self, params: schemas.LoginRequest) -> models.User | None:
        self.__logger.info(f"Login attempt for: {params.email}")
        user = self.__user_service.authenticate(
            params.email, params.password.get_secret_value()
        )
        if user:
            self.__logger.info(
                f"Login successful for: {params.email} (role={user.role})"
            )
        else:
            self.__logger.warning(f"Login failed for: {params.email}")
        return user

    def register(self, params: schemas.CreateUser) -> models.User:
        self.__logger.info(f"Registration attempt: {params.email} as {params.role}")
        user = self.__user_service.create_user(params)
        self.__logger.info(f"Registration successful: {params.email}")
        return user
