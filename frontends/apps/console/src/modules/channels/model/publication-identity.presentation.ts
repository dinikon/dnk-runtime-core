import type {
  PublicationIdentityState,
  PublicationIdentitySummary,
} from "./publication-identity.types";
export const identityLabels: Record<PublicationIdentityState, string> = {
  missing: "Без ключа",
  duplicate: "Дублирующийся ключ",
  valid: "Ключ указан",
  not_required: "Не требуется",
};
export const identityAssessmentLabels: Record<
  PublicationIdentitySummary["assessment"],
  string
> = {
  not_started: "Загрузка ещё не выполнялась. Диагностика предварительная.",
  in_progress: "Загрузка продолжается. Счётчики могут измениться.",
  current: "Проверено среди загруженных публикаций.",
  stale:
    "Настройки подключения изменились. Обновите публикации для актуальной проверки.",
  incomplete:
    "Последняя загрузка неполная. Отсутствие дублей ещё не подтверждено.",
};
export function parseIdentityStatus(value: unknown): string {
  return typeof value === "string" &&
    ["missing", "duplicate", "valid"].includes(value)
    ? value
    : "";
}
