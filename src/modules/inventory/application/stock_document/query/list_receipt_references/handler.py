from src.modules.inventory.application.stock_document.port.receipt_posting import ReceiptFactsQueryPort
from src.modules.inventory.application.stock_document.query.list_receipt_references.query import ListReceiptReferencesQuery
from src.modules.inventory.application.stock_document.query.list_receipt_references.dto import ListReceiptReferencesResultDTO
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
class ListReceiptReferencesHandler:
    """Читает варианты выбора без команд и скрытого создания справочников."""
    def __init__(self,repository:ReceiptFactsQueryPort)->None:
        """Получает порт проекции текущего tenant."""
        self._repository=repository
    async def execute(self,query:ListReceiptReferencesQuery)->ListReceiptReferencesResultDTO:
        """Возвращает страницу либо сообщает об отсутствии документа или его строки."""
        result=await self._repository.references(query)
        if result is None:raise StockDocumentNotFoundError("Документ или строка не найдены.")
        return result
