import axios from "axios";
import { representationIssueMessage } from "./representation.errors";

const labels: Record<string, string> = {
  content_parent_changed:
    "Родительская публикация изменилась или недоступна. Обновите публикации и сопоставления.",
  content_preview_changed:
    "Контент изменился. Обновите preview и проверьте его перед отправкой.",
  content_context_changed:
    "Данные или разрешение изменились до отправки. Проверьте актуальное представление.",
  content_export_disabled:
    "Сначала сохраните представление и разрешите экспорт.",
  content_reconciliation_required:
    "Результат не подтверждён. Повторная отправка остановлена до надёжной сверки с площадкой.",
  content_provider_response_mismatch:
    "Ответ площадки не подтверждает все отправленные поля. Нужна сверка.",
  content_worker_interrupted:
    "Выполнение прервано. Сначала сверьте результат с площадкой.",
  content_revision_conflict:
    "Состояние доставки изменилось. Перечитайте результаты.",
  content_attempt_active: "Обновление или сверка уже выполняется.",
  content_variation_title_unsupported:
    "WooCommerce формирует название вариации из товара и атрибутов. Уберите индивидуальное переопределение названия.",
  media_variation_gallery_unsupported:
    "Для вариации в этом режиме поддерживается одно изображение.",
  media_caption_unsupported:
    "Подписи изображений не поддерживаются этим режимом WooCommerce.",
  content_access_denied: "У инициатора больше нет права управлять каналом.",
  content_file_forbidden:
    "У инициатора нет права использовать одно из изображений.",
  content_connection_changed:
    "Подключение изменилось. Старый запрос не отправляется с новыми настройками.",
  content_media_changed:
    "Состояние изображения изменилось во время передачи. Требуется сверка.",
  content_media_unconfirmed:
    "Площадка не подтвердила соответствие одного из изображений.",
  content_provider_response_invalid:
    "Ответ площадки не удалось проверить. Перечитайте результат или выполните сверку.",
  content_target_changed:
    "Тип или адрес публикации изменился. Обновите публикации и сопоставления.",
  content_request_unreadable:
    "Сохранённый запрос не удалось расшифровать. Требуется восстановление конфигурации шифрования.",
  provider_unavailable:
    "Площадка временно недоступна. Возможный результат записи нужно сверить.",
  endpoint_unreachable:
    "Не удалось связаться с площадкой. Проверьте подключение и результат доставки.",
  invalid_credentials: "Площадка отклонила ключи подключения.",
  rate_limited:
    "Площадка ограничила частоту запросов. Повторите проверку позднее.",
  network_timeout:
    "Площадка не ответила вовремя. Перед повтором требуется сверка.",
  permission_missing: "Площадка не разрешает обновление этой публикации.",
};

export function contentDeliveryIssue(code: string): string {
  return labels[code] ?? representationIssueMessage(code);
}

export function contentDeliveryError(error: unknown): string {
  const code = axios.isAxiosError(error)
    ? error.response?.data?.detail?.code
    : undefined;
  return typeof code === "string"
    ? contentDeliveryIssue(code)
    : "Не удалось получить результат. Перечитайте состояние перед повторным запуском.";
}
