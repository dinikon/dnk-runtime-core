from cryptography.fernet import Fernet


class CredentialCipher:
    def __init__(self, key: str):
        if hasattr(key, "get_secret_value"):
            key = key.get_secret_value()
        self._cipher = Fernet(key.encode("ascii"))

    def encrypt(self, secret: str) -> str:
        return self._cipher.encrypt(secret.encode()).decode("ascii")

    def decrypt(self, encrypted: str) -> str:
        return self._cipher.decrypt(encrypted.encode("ascii")).decode()
