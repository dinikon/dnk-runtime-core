from uuid import UUID


class SchemaIdVO:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("SchemaIdVO value must be UUID")

    def __str__(self) -> str:
        return str(self.value)
