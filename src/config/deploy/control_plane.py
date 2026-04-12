from pydantic import Field
from pydantic_settings import BaseSettings


class ControlPlaneConfig(BaseSettings):
    CONTROL_PLANE_API_KEY: str = Field(
        default="",
        description="Shared API key for ControlPlane server-to-server requests.",
    )
