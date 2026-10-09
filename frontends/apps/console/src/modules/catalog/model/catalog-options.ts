import { catalogApi } from "../api/catalog.api";
import { typeFromDto, blockFromDto } from "../api/catalog.mapper";
export async function loadTypes(locale: string, signal?: AbortSignal) {
  const first = await catalogApi.listProductTypes(locale, "", 1, 100, signal);
  const items = [...first.items];
  for (let page = 2; items.length < first.total; page++) {
    items.push(
      ...(await catalogApi.listProductTypes(locale, "", page, 100, signal))
        .items,
    );
  }
  return items.map(typeFromDto);
}
export async function loadBlocks(locale: string, signal?: AbortSignal) {
  const first = await catalogApi.listContentBlocks(locale, "", 1, 100, signal);
  const items = [...first.items];
  for (let page = 2; items.length < first.total; page++) {
    items.push(
      ...(await catalogApi.listContentBlocks(locale, "", page, 100, signal))
        .items,
    );
  }
  return items.map(blockFromDto);
}
