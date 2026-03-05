class MockCrmEntityNotFoundError(Exception):
    def __init__(self, entity_key: str) -> None:
        super().__init__(f"CRM entity mock not found: {entity_key}")
        self.entity_key = entity_key
