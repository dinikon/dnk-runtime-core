import type { FeedStatus, FeedValidationPolicy } from "./feed.types";
export const feedStatuses: Record<FeedStatus, string> = {
  DRAFT: "Черновик",
  ACTIVE: "Активен",
  PAUSED: "Приостановлен",
  ARCHIVED: "В архиве",
};
export const feedValidationLabels: Record<FeedValidationPolicy, string> = {
  STRICT: "Строгая проверка",
  SKIP_INVALID: "Пропуск позиций с ошибками",
};
