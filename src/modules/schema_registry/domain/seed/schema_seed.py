from dataclasses import dataclass

from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed


@dataclass(frozen=True, slots=True)
class SchemaSeed:
    version: str | None
    code: str
    label: str
    objects: tuple[ObjectSeed, ...]

    def get_object(self, object_name: str) -> ObjectSeed | None:
        normalized = object_name.strip()
        for item in self.objects:
            if item.singular_name == normalized or item.plural_name == normalized:
                return item
        return None
