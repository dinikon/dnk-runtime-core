const statuses: Record<string, string> = {
  SELLABLE: "Пригодный к продаже",
  QUARANTINE: "Карантин",
  DAMAGED: "Повреждённый",
  BLOCKED: "Заблокированный",
};
const operations: Record<string, string> = {
  RECEIPT: "Поступление",
  ISSUE: "Расход",
  WRITE_OFF: "Списание",
  RETURN: "Возврат",
  STATUS_CHANGE: "Изменение состояния",
  INTERNAL_MOVE: "Перемещение",
  ADJUSTMENT: "Корректировка",
};
const documents: Record<string, string> = {
  DRAFT: "Черновик",
  CONFIRMED: "Подтверждён",
  PARTIALLY_EXECUTED: "Частично выполнен",
  COMPLETED: "Выполнен",
  CANCELLED: "Отменён",
};
export function stockStatusLabel(value: string): string {
  return statuses[value] ?? value;
}
export function stockOperationLabel(value: string): string {
  return operations[value] ?? value;
}
export function stockDocumentStatusLabel(value: string): string {
  return documents[value] ?? value;
}
