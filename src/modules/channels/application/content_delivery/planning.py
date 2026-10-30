from hashlib import sha256
import json

from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
)


def content_fingerprint(value: PreparedRepresentation) -> str:
    """Хеширует значимые значения и адреса целей без времени, URL и ревизии разрешения."""
    targets = [
        [
            str(target.publication_id.uuid),
            target.external_id,
            (
                str(target.parent_publication_id.uuid)
                if target.parent_publication_id
                else None
            ),
            target.publication_kind,
            target.role.value,
            [
                [
                    content.locale,
                    content.title,
                    content.body,
                    (
                        [
                            [str(image.file_id.uuid), image.alt, image.caption]
                            for image in content.gallery
                        ]
                        if content.gallery is not None
                        else None
                    ),
                ]
                for content in target.content
            ],
        ]
        for target in sorted(
            value.preparation.targets,
            key=lambda target: (
                target.role.value != "container",
                str(target.publication_id.uuid),
            ),
        )
    ]
    return sha256(
        json.dumps(
            [value.platform, list(value.locales), targets],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
