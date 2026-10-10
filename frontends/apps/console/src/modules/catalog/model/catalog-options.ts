import { categoryFromDto, tagFromDto } from "../api/catalog.mapper";
import { catalogApi } from "../api/catalog.api";
import {
  typeFromDto,
  blockFromDto,
  attributeFromDto,
} from "../api/catalog.mapper";
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

export async function loadAttributes(locale: string, signal?: AbortSignal) {
  const first = await catalogApi.listAttributes(locale, "", 1, 100, signal);
  const items = [...first.items];
  for (let page = 2; items.length < first.total; page++)
    items.push(
      ...(await catalogApi.listAttributes(locale, "", page, 100, signal)).items,
    );
  return Promise.all(
    items.map(async (item) =>
      attributeFromDto(await catalogApi.getAttribute(item.id, locale, signal)),
    ),
  );
}

export async function loadCategories(locale: string, signal?: AbortSignal) {
  const first = await catalogApi.listCategories(locale, "", 1, 100, signal);
  const items = [...first.items];
  for (let page = 2; items.length < first.total; page++)
    items.push(
      ...(await catalogApi.listCategories(locale, "", page, 100, signal)).items,
    );
  return items.map(categoryFromDto);
}
export async function loadTags(locale: string, signal?: AbortSignal) {
  const first = await catalogApi.listTags(locale, "", 1, 100, signal);
  const items = [...first.items];
  for (let page = 2; items.length < first.total; page++)
    items.push(
      ...(await catalogApi.listTags(locale, "", page, 100, signal)).items,
    );
  return items.map(tagFromDto);
}
