from src.modules.shared.domain.errors import ValidationError


class UserEmailAlreadyExistsError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"User email '{email}' already exists in tenant.")
