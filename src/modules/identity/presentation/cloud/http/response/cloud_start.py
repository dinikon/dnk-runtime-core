from pydantic import BaseModel


class CloudStartResponse(BaseModel):
    """Адрес перехода к доверенному OIDC-провайдеру."""

    authorization_url: str
