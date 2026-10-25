import type { ImportStatus } from "./import.types";
export const importStatusLabels: Record<ImportStatus, string> = {
  preparing: "Подготовка",
  mapping: "Сопоставление",
  queued: "В очереди",
  running: "Выполняется",
  cancelling: "Остановка",
  cancelled: "Остановлен",
  completed: "Завершён",
  completed_with_errors: "Завершён с ошибками",
  failed: "Сбой",
  expired: "Черновик истёк",
};
export const importTargets = [
  ["sku", "SKU"],
  ["title", "Название"],
  ["body", "Описание"],
  ["status", "Статус товара"],
  ["virtual", "Услуга / virtual"],
  ["regular_price", "Обычная цена"],
  ["currency", "Валюта"],
  ["sale_price", "Акционная цена"],
  ["discount", "Скидка Prom"],
  ["date_on_sale_from", "Начало скидки"],
  ["date_on_sale_to", "Конец скидки"],
  ["manage_stock", "Учёт количества"],
  ["stock_quantity", "Количество"],
  ["stock_status", "Наличие"],
  ["backorders", "Предзаказ"],
  ["weight", "Вес"],
  ["weight_unit", "Единица веса"],
  ["length", "Длина"],
  ["length_unit", "Единица длины"],
  ["width", "Ширина"],
  ["width_unit", "Единица ширины"],
  ["height", "Высота"],
  ["height_unit", "Единица высоты"],
  ["images", "Изображения — URL"],
  ["image_alt", "Alt изображений"],
  ["image_caption", "Подписи изображений"],
  ["primary_image", "Номер главного фото"],
] as const;
export const localizedImportTargets = new Set([
  "title",
  "body",
  "images",
  "image_alt",
  "image_caption",
  "primary_image",
]);
export function importIsActive(status: ImportStatus): boolean {
  return ["preparing", "queued", "running", "cancelling"].includes(status);
}
export function importIsFinished(status: ImportStatus): boolean {
  return [
    "cancelled",
    "completed",
    "completed_with_errors",
    "failed",
    "expired",
  ].includes(status);
}
