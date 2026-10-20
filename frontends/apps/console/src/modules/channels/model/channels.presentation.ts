import { settingsSchemaSupported } from "./settings-schema.ts";
import type { Connection, Initialization, Platform } from "./channels.types";
const verificationLabels: Record<string, string> = {
  unverified: "Не проверено",
  queued: "Проверка доступа…",
  verified: "Доступ подтверждён",
  error: "Ошибка проверки",
};
export function verificationLabel(status: string | null): string {
  return status
    ? (verificationLabels[status] ?? "Неизвестное состояние подключения")
    : "Не настроено";
}
const reasons: Record<string, string> = {
  content_update_not_found:
    "Операция обновления не найдена или недоступна в текущем рабочем пространстве.",
  import_worker_interrupted:
    "Фоновая загрузка прервалась. Повторите подготовку: уже готовые фотографии сохранятся.",
  import_source_changed:
    "Публикация или настройки подключения изменились. Получите карточку заново.",
  import_preparation_expired:
    "Срок подготовки истёк. Получите карточку заново.",
  image_network_error:
    "Не удалось скачать фотографию. Повторите перенос или исключите её.",
  image_download_failed:
    "Источник не отдал фотографию. Повторите перенос или исключите её.",
  image_storage_failed:
    "Не удалось сохранить фотографию в хранилище. Повторите перенос.",
  unsupported_image_format:
    "Формат фотографии не поддерживается. Доступны PNG, JPEG, WebP, GIF, AVIF и BMP.",
  invalid_image_file: "Источник передал некорректный файл изображения.",
  image_too_large: "Фотография превышает допустимый размер 10 MiB.",
  unsafe_image_url:
    "Фотография недоступна по разрешённому публичному HTTPS-адресу.",
  publication_gallery_limit_exceeded:
    "Галерея источника превышает лимит каталога: 100 фотографий.",
  invalid_publication_gallery: "Источник передал некорректную галерею.",
  invalid_publication_description: "Не удалось прочитать описание источника.",
  title_inherited_from_parent:
    "Название получено из родительского товара вариации.",
  description_inherited_from_parent:
    "Описание получено из родительского товара вариации.",
  gallery_inherited_from_parent:
    "Галерея получена из родительского товара вариации.",
  publication_locales_mismatch:
    "Полученные языки не соответствуют настройкам подключения.",
  api_visible_statuses_only:
    "Загружены публикации, доступные через API. Недоступные и удалённые записи могут отсутствовать.",
  quantity_not_exposed: "Источник не передаёт количество.",
  sale_price_semantics_unverified:
    "Акционная цена не подтверждена контрактом источника.",
  content_update_update_only_unconfirmed:
    "Отправка XML в Prom недоступна: публичный API импорта не документирует запрет создания новых карточек. Сравнение текстов доступно.",
  content_update_write_unsupported:
    "Плагин пока не поддерживает безопасную отправку текстов.",
  content_update_target_unsupported:
    "Для этого типа публикации обновление названия и описания не поддерживается. Родительский товар автоматически не изменяется.",
  catalog_content_missing:
    "Заполните название и описание в каталоге на всех локалях подключения. Пустые значения не отправляются.",
  catalog_content_changed:
    "Тексты каталога изменились. Пересоберите сравнение и подтвердите его заново.",
  catalog_content_unavailable:
    "Товар каталога недоступен для подготовки обновления.",
  external_content_changed:
    "Тексты площадки изменились после сравнения. Пересоберите сравнение.",
  content_update_binding_changed:
    "Связь публикации с каталогом изменилась. Пересоберите сравнение.",
  content_update_binding_required:
    "Для обновления каждая выбранная публикация должна быть связана с каталогом этого канала.",
  content_update_target_busy:
    "Для одной из публикаций есть незавершённая или непроверенная отправка. Откройте её результат и выполните сверку.",
  content_update_preview_stale:
    "Сравнение устарело. Подготовьте новое перед отправкой.",
  content_update_revision_conflict:
    "Состояние операции изменилось. Обновите страницу и повторите действие.",
  content_update_no_changes: "Названия и описания уже совпадают с каталогом.",
  content_update_verification_mismatch:
    "Площадка пока возвращает другие тексты. Проверьте результат ещё раз или пересоберите сравнение.",
  content_update_expired: "Срок действия сравнения истёк. Подготовьте новое.",
  content_update_plugin_changed: "Плагин обновился. Пересоберите сравнение.",
  content_update_in_progress:
    "Операция ещё выполняется. Дождитесь следующего шага.",
  content_update_retry_unavailable:
    "Для текущего состояния продолжение недоступно. Пересоберите сравнение.",
  outbound_sync_disabled:
    "Исходящие операции канала выключены. Сначала явно разрешите обновления.",
  publication_not_found:
    "Публикация больше не найдена на площадке. Новая карточка не создавалась.",
  permission_denied:
    "Источник отклонил ключи или у них недостаточно прав. Проверьте доступ и повторите проверку.",
  publication_revision_conflict:
    "Публикация обновилась после preview. Обновите данные источника и подтвердите перенос.",
  publication_already_bound:
    "Эта публикация уже связана с товаром. Обновите список и откройте связанный товар.",
  catalog_item_already_bound:
    "У этого товара уже есть основная публикация в данном канале.",
  catalog_item_archived: "Архивный товар недоступен для новой связи.",
  binding_revision_conflict:
    "Связь изменилась. Обновите список и повторите выбор.",
  idempotency_key_reused:
    "Этот ключ запроса уже использован с другим набором значений.",
  resource_identity_in_use: "Этот магазин уже подключён к другому каналу.",
  network_error: "Не удалось связаться с источником. Повторите позже.",
  provider_temporarily_unavailable:
    "Источник временно недоступен. Повторите позже.",
  provider_request_rejected:
    "Источник отклонил запрос. Проверьте настройки подключения.",
  invalid_sale_price:
    "Акционную цену не удалось определить по данным источника. Проверьте её вручную.",
  invalid_price: "Источник передал некорректную базовую цену.",
  invalid_quantity: "Источник передал некорректное количество.",
  source_timezone_unknown:
    "Источник не указал часовой пояс времени обновления.",
  truncated_title:
    "Название источника превышает допустимую длину. Проверьте сокращённый текст.",
  invalid_title: "Источник передал некорректное название.",
  invalid_provider_response: "Источник вернул неподдерживаемый ответ.",
  unsafe_endpoint:
    "Адрес источника не прошёл проверку безопасности. Укажите публичный HTTPS-адрес магазина.",
  currency_unknown: "Источник не указал валюту.",
  title_missing: "Источник не передал название.",
  invalid_main_image_url:
    "Изображение источника недоступно по безопасному адресу.",
  scope_limited: "Завершено в пределах доступного охвата API.",
  resource_change_requires_new_channel:
    "Для другого магазина создайте новый канал.",
  revision_conflict:
    "Данные изменились. Проверьте актуальную версию и повторите сохранение.",
  invalid_settings_shape:
    "Проверьте настройки подключения: значения не соответствуют схеме платформы.",
  settings_too_large: "Настройки подключения слишком велики.",
  invalid_credentials_shape: "Проверьте заполнение полей доступа.",
  primary_locale_not_allowed: "Основной язык этой платформы фиксирован.",
  additional_locale_not_allowed:
    "Дополнительный язык недоступен для этой платформы.",
  currency_required: "Выберите валюту ресурса.",
  currency_not_allowed: "Валюта этой платформы фиксирована.",
  credentials_encryption_not_configured:
    "Хранение ключей доступа ещё не настроено на сервере.",
  connection_paused: "Подключение приостановлено.",
  channel_archived: "Канал архивирован.",
  plugin_not_registered: "Плагин этой платформы недоступен.",
  invalid_credentials: "Источник отклонил данные доступа.",
  unauthorized: "Источник отклонил данные доступа.",
  forbidden: "Недостаточно прав доступа к источнику.",
};
export function reasonLabel(code: string): string {
  return reasons[code] ?? `Дополнительная информация: ${code}`;
}
export function initializationLabel(run: Initialization): string {
  if (run.recoveryRequired) return "Загрузка требует восстановления";
  if (run.status === "partial")
    return run.readComplete
      ? "Загрузка завершена с ограничениями"
      : "Загрузка прервана, часть данных сохранена";
  return (
    (
      {
        not_started: "Загрузка ещё не началась",
        queued: "Загрузка в очереди",
        running: "Загружаем публикации…",
        succeeded: "Загрузка завершена",
        failed: "Ошибка загрузки",
        cancelled: "Загрузка остановлена",
      } as Record<string, string>
    )[run.status] ?? "Неизвестное состояние загрузки"
  );
}
export function initializationActive(run: Initialization | undefined): boolean {
  return (
    !!run && !run.recoveryRequired && ["queued", "running"].includes(run.status)
  );
}
export function connectionActive(
  connection: Connection | undefined,
  archived: boolean,
): boolean {
  return !!connection && !connection.isPaused && !archived;
}
export function platformSupported(platform: Platform): boolean {
  const schema = platform.credentialsSchema;
  const fields = Object.entries(schema?.properties ?? {});
  return (
    platform.sdkVersion === 5 &&
    platform.configVersion === 3 &&
    settingsSchemaSupported(platform.settingsSchema) &&
    platform.endpointSchema?.type === "string" &&
    schema?.type === "object" &&
    fields.length > 0 &&
    fields.every(
      ([, field]) =>
        field.type === "string" &&
        Object.keys(field).every((key) =>
          [
            "type",
            "title",
            "description",
            "minLength",
            "maxLength",
            "writeOnly",
          ].includes(key),
        ),
    ) &&
    (schema.required ?? []).every((key) =>
      fields.some(([name]) => key === name),
    )
  );
}
export function decimalLabel(
  value: string | null,
  currency?: string | null,
): string {
  if (value === null) return "—";
  // Expand a Decimal exponent and trim insignificant zeros using string operations only.
  const match = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return value;
  const exponent = Number(match[4] ?? "0");
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 1000)
    return value;
  const whole = match[2] ?? "0",
    fraction = match[3] ?? "",
    digits = whole + fraction,
    point = whole.length + exponent;
  const expanded =
    point <= 0
      ? "0." + "0".repeat(-point) + digits
      : point >= digits.length
        ? digits + "0".repeat(point - digits.length)
        : digits.slice(0, point) + "." + digits.slice(point);
  const [integer = "0", decimal = ""] = expanded.split(".");
  const significant = decimal.replace(/0+$/, "");
  const formatted =
    integer.replace(/^0+(?=\d)/, "") + (significant ? "." + significant : "");
  return `${match[1] === "-" && formatted !== "0" ? "-" : ""}${formatted}${currency ? ` ${currency}` : ""}`;
}
export function dateLabel(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "—" : date.toLocaleString("ru-RU");
}
export const stockLabels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_backorder: "Под заказ",
  unknown: "Неизвестно",
};
