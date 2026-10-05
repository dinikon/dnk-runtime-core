import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
export const isUuid = (value: string) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
export const contentPayload = (name: string, description: string) => ({
  name: name.trim(),
  description: description.trim() || null,
});
export const validName = (name: string) => {
  const length = Array.from(name.trim()).length;
  return length >= 1 && length <= 255;
};
export function catalogError(error: unknown) {
  const messages: Record<number, string> = {
    403: "Недостаточно прав для выполнения операции.",
    404: "Товар или выбранный SKU не найден.",
    409: "Не удалось создать товар: конфликт данных.",
    422: "Проверьте данные формы и доступность выбранного языка.",
  };
  return (
    messages[getApiErrorStatus(error) ?? 0] ??
    getApiErrorMessage(
      error,
      "Не удалось выполнить запрос. Попробуйте ещё раз.",
    )
  );
}
