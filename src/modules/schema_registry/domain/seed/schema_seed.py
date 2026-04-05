from dataclasses import dataclass

from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed


@dataclass(frozen=True, slots=True)
class SchemaSeed:
    version: str | None
    code: str
    label: str
    objects: tuple[ObjectSeed, ...]

    def get_object(self, object_name: str) -> ObjectSeed | None:
        for item in self.objects:
            if item.name == object_name:
                return item
        return None
