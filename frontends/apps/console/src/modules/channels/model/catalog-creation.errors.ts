import axios from "axios";
import { channelErrorMessage } from "./channel.errors";
const messages: Record<string, string> = {
  publication_structure_changed:
    "Товар или его варианты изменились. Синхронизируйте публикации и повторите создание.",
  publication_details_unavailable:
    "У позиции нет идентификатора для получения деталей площадки. Синхронизируйте публикации.",
  catalog_values_invalid:
    "Данные площадки не подходят для Catalog. Проверьте название, цены, наличие, целое количество и языки товара.",
  publication_images_limit:
    "В галерее превышен допустимый размер. Товар не создан.",
  catalog_sku_changed: "SKU изменился во время создания. Повторите действие.",
  catalog_creation_conflict:
    "Данные изменились во время создания. Обновите список и повторите действие.",
};
export function publicationCatalogError(cause: unknown): string {
  const code = axios.isAxiosError(cause)
    ? cause.response?.data?.detail?.code
    : undefined;
  return typeof code === "string" && messages[code]
    ? messages[code]
    : channelErrorMessage(typeof code === "string" ? code : cause);
}
