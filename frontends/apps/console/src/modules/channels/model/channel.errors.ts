import { ChannelApiError } from "./channel.types";
const messages: Record<string, string> = {
  invalid_credentials:
    "Площадка отклонила данные доступа. Проверьте доступ и сохраните новые значения.",
  permission_missing:
    "Доступ подтверждён не полностью: не хватает прав для проверки магазина.",
  resource_identity_unavailable: "Не удалось однозначно определить магазин.",
  resource_identity_changed:
    "Этот доступ относится к другому магазину. Создайте для него новый канал.",
  resource_already_connected: "Этот магазин уже подключён другим каналом.",
  provider_response_invalid: "Площадка вернула неожиданный ответ.",
  endpoint_invalid:
    "Нужен публичный HTTPS-адрес магазина без параметров и данных авторизации.",
  endpoint_redirected:
    "Магазин перенаправляет запрос. Укажите его конечный HTTPS-адрес.",
  network_timeout: "Площадка не ответила вовремя. Повторите проверку.",
  endpoint_unreachable: "Не удалось связаться с площадкой.",
  provider_unavailable: "API площадки временно недоступен.",
  rate_limited: "Площадка временно ограничила число запросов.",
  credentials_unreadable:
    "Сохранённый доступ не удалось расшифровать. Замените данные доступа или проверьте ключ сервера.",
  channels_not_configured: "На сервере не настроен ключ шифрования Channels.",
  revision_conflict:
    "Канал уже изменён. Актуальные данные загружены; ваш черновик сохранён. Сверьте изменения и сохраните ещё раз.",
  channel_not_found: "Канал удалён или недоступен.",
  access_denied: "Недостаточно прав для этого действия.",
  credentials_invalid: "Заполните полный комплект данных доступа.",
  currency_unavailable: "Валюта отсутствует в справочнике или недоступна.",
  locale_unavailable: "Язык контента отсутствует в справочнике или недоступен.",
  configuration_invalid: "Проверьте настройки подключения.",
  request_invalid: "Проверьте обязательные поля формы.",
  name_invalid: "Введите название канала длиной до 255 символов.",
};
export function channelErrorMessage(error: unknown): string {
  const code =
    error instanceof ChannelApiError
      ? error.code
      : typeof error === "string"
        ? error
        : "";
  return (
    messages[code] ??
    "Не удалось выполнить запрос. Проверьте состояние канала перед повторной отправкой."
  );
}
