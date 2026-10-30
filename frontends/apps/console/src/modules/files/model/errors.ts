import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import axios from "axios";
export function fileError(cause: unknown): string {
  const status = getApiErrorStatus(cause);
  if (
    status === 409 &&
    axios.isAxiosError(cause) &&
    cause.response?.data?.detail?.code === "file_in_use"
  )
    return "Файл используется. Удалите его из галерей каталога и каналов или дождитесь завершения передачи.";
  const messages: Record<number, string> = {
    403: "Недостаточно прав или истекла защита сессии. Обновите страницу.",
    404: "Файл или диск больше недоступен. Обновите список.",
    409: "Состояние файла или диска изменилось; срок восстановления мог истечь. Обновите список.",
    413: "Файл превышает допустимый размер на сервере.",
    408: "Время загрузки истекло. Проверьте список перед повторной попыткой.",
    422: "Проверьте имя файла и выбранный диск.",
    503: "Хранилище временно недоступно. Попробуйте позже.",
  };
  return status && messages[status]
    ? messages[status]
    : getApiErrorMessage(
        cause,
        "Не удалось выполнить запрос. Проверьте соединение и обновите список.",
      );
}
