import { ChannelApiError } from "./channel.types";
import { channelErrorMessage } from "./channel.errors";
const messages: Record<string, string> = {
  stock_tracking_required: "Включите количественный учёт у товара Catalog.",
  stock_negative_unsupported:
    "Отправка отрицательного количества пока не поддерживается.",
  stock_ownership_ambiguous:
    "Неоднозначное сопоставление общих и собственных остатков. Проверьте учёт количества у вариантов и их связи.",
  stock_export_forbidden: "В настройках канала запрещена отправка остатков.",
  stock_connection_unverified: "Сначала проверьте подключение канала.",
  stock_binding_not_found: "Связь недоступна. Обновите список публикаций.",
  stock_selection_invalid:
    "Выбранные позиции больше не принадлежат этой связи.",
  stock_write_identity_unavailable:
    "У позиции нет подтверждённого ID Rozetka для отправки.",
  stock_source_api_required:
    "В кабинете Rozetka источник должен разрешать управление остатками через API.",
  stock_backorders_unsupported:
    "Площадка не поддерживает выбранную политику предзаказа.",
  stock_status_unsupported:
    "Площадка не поддерживает отправку выбранного ручного наличия. Позиция пропущена.",
  stock_dependency_failed:
    "Не удалось обновить родителя. Зависимая позиция не отправлена.",
  stock_operation_in_progress:
    "Дождитесь завершения текущей синхронизации семьи.",
  stock_unmapped_inheritors:
    "Изменение общего родителя влияет также на несопоставленные варианты площадки. Их собственные настройки не изменяются.",
  stock_write_rejected: "Площадка отклонила изменение остатка.",
  stock_write_unconfirmed:
    "Площадка пока не подтвердила остаток или наличие после отправки.",
  stock_job_interrupted: "Выполнение прервано. Повторите действие.",
};
export function stockCodeMessage(code: string | null): string {
  return code
    ? (messages[code] ?? channelErrorMessage(new ChannelApiError(code)))
    : "";
}
export function stockErrorMessage(error: unknown): string {
  return error instanceof ChannelApiError
    ? stockCodeMessage(error.code)
    : channelErrorMessage(error);
}
