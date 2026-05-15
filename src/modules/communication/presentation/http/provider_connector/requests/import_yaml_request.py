from pydantic import BaseModel


class ImportYamlRequestSchema(BaseModel):
    """Pydantic-схема тела запроса импорта provider connector YAML."""

    yaml_content: str


__all__ = ["ImportYamlRequestSchema"]
