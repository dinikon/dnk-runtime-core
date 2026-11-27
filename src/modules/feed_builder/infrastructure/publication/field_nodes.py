from src.modules.feed_builder.domain.publication.field_node.registry import (
    build_publication_nodes,
)
from src.modules.shared.infrastructure.content.rich_text import sanitize_rich_text

PUBLICATION_FIELD_NODES = build_publication_nodes(sanitize_rich_text)
