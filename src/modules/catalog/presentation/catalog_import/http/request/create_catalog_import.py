from pydantic import BaseModel, ConfigDict, Field
from fastapi import UploadFile


class CreateCatalogImportRequest(BaseModel):
    """Ровно один источник и начальный язык/часовой пояс мастера."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    file: UploadFile | None = None
    url: str | None = Field(default=None, max_length=4096)
    default_locale: str = Field(default="uk", min_length=1, max_length=64)
    timezone: str = Field(default="Europe/Kyiv", min_length=1, max_length=100)

    @classmethod
    def openapi_body(cls) -> dict[str, object]:
        """Описывает оба реально поддержанных Content-Type одного endpoint."""
        properties = cls.model_json_schema()["properties"]
        return {
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["url"],
                            "properties": {
                                key: value
                                for key, value in properties.items()
                                if key != "file"
                            },
                        }
                    },
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["file"],
                            "properties": {
                                key: value
                                for key, value in properties.items()
                                if key != "url"
                            },
                        }
                    },
                },
            }
        }
