from src.modules.inventory.application.stock_document.port.receipt_posting import ReceiptFactsQueryPort
from src.modules.inventory.application.stock_document.query.prepare_receipt.query import PrepareReceiptQuery
from src.modules.inventory.application.stock_document.query.prepare_receipt.dto import PrepareReceiptResultDTO
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
class PrepareReceiptHandler:
    """Читает подготовку формы через специализированную проекцию."""
    def __init__(self,repository:ReceiptFactsQueryPort)->None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository=repository
    async def execute(self,query:PrepareReceiptQuery)->PrepareReceiptResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result=await self._repository.prepare(query)
        if result is None:raise StockDocumentNotFoundError("Поступление не найдено.")
        return result
