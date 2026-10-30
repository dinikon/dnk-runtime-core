import type { FeedImport } from "./content-feed.types";
export function feedSubmissionLabel(value: FeedImport): string {
  return {
    not_sent: "Не отправлено",
    queued: "Ожидает отправки",
    submitting: "Передаём ссылку",
    accepted: "Ссылка принята",
    rejected: "Запрос отклонён",
    unknown: "Результат передачи неизвестен",
  }[value.submission];
}
export function feedReportLabel(value: FeedImport): string {
  if (value.report)
    return {
      SUCCESS: "Импорт завершён",
      PARTIAL: "Импорт завершён частично",
      FATAL: "Ошибка импорта",
    }[value.report.status];
  if (value.phase === "processing") return "Ожидаем отчёт Prom";
  if (value.phase === "needs_attention") return "Наблюдение приостановлено";
  if (value.phase === "unknown") return "Нужен ID импорта";
  return "Отчёта пока нет";
}
export function feedVerificationLabel(value: FeedImport): string {
  const fields = value.verification.flatMap((v) => v.fields);
  if (fields.some((f) => f.status === "obsolete"))
    return "Представление изменилось";
  if (fields.some((f) => f.status === "mismatch")) return "Есть расхождения";
  if (fields.some((f) => f.status === "unconfirmed"))
    return "Применение подтверждено не полностью";
  if (
    fields.length &&
    value.phase === "completed" &&
    !value.errorCode &&
    fields.every((f) => f.status === "confirmed")
  )
    return "Контент подтверждён";
  return value.phase === "verifying"
    ? "Проверяем поля"
    : "Применение ещё не подтверждено";
}
export function feedFieldLabel(field: string): string {
  return (
    { title: "Название", body: "Описание", gallery: "Галерея" }[field] ?? field
  );
}
export function feedFieldStatus(status: string): string {
  return (
    {
      confirmed: "Подтверждено",
      mismatch: "Расхождение",
      unconfirmed: "Не подтверждено",
      obsolete: "Снимок устарел",
    }[status] ?? "Не подтверждено"
  );
}
export function feedDate(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat("ru", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "—";
}
