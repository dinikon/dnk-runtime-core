import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
export function validSkuCode(value: string) {
  const code = value.trim();
  const length = Array.from(code).length;
  return (
    length >= 1 &&
    length <= 128 &&
    !Array.from(code).some(
      (char) => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127,
    )
  );
}
export function validSkuTitle(value: string) {
  const length = Array.from(value.trim()).length;
  return length >= 1 && length <= 255;
}
export function inventoryError(error: unknown) {
  const messages: Record<number, string> = {
    403: "Недостаточно прав для работы с SKU.",
    404: "SKU не найден или недоступен.",
    409: "SKU с таким кодом уже существует. Укажите другой код.",
    422: "Проверьте код и название SKU.",
  };
  return (
    messages[getApiErrorStatus(error) ?? 0] ??
    getApiErrorMessage(
      error,
      "Не удалось выполнить запрос SKU. Попробуйте ещё раз.",
    )
  );
}
