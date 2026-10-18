import {
  itemFromDto,
  listItemFromDto,
  updateItemToDto,
  schemaFromDto,
} from "./catalog.mapper";
import type {
  CatalogItem,
  CatalogItemsPage,
  CatalogSchema,
} from "../model/catalog.types";
import type { ProductPatch, ProductStatus } from "../model/product.types";
import { httpClient } from "@/app/providers/http";
import type * as DTO from "./catalog.dto";
const base = "/console/catalog";
export const catalogApi = {
  async locales(
    signal?: AbortSignal,
  ): Promise<{ code: string; name: string }[]> {
    return (
      await httpClient.get<DTO.LocaleDTO[]>("/console/reference-data/locales", {
        signal,
      })
    ).data;
  },
  async listItems(
    locale: string,
    search = "",
    offset = 0,
    limit = 20,
    status?: ProductStatus,
    signal?: AbortSignal,
  ): Promise<CatalogItemsPage> {
    const { data } = await httpClient.get<DTO.ListItemsResponse>(
      base + "/items",
      {
        params: { locale, search, offset, limit, status },
        signal,
      },
    );
    return { ...data, items: data.items.map(listItemFromDto) };
  },
  async getItem(
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<CatalogItem> {
    const { data } = await httpClient.get<DTO.GetItemResponse>(
      base + `/items/${encodeURIComponent(id)}`,
      { params: { locale }, signal },
    );
    return itemFromDto(data.item);
  },
  async createItem(virtual = false): Promise<{ id: string }> {
    return (
      await httpClient.post<DTO.CreateItemResponse>(base + "/items", {
        virtual,
      })
    ).data;
  },
  async updateItem(
    id: string,
    value: ProductPatch,
    locale?: string,
  ): Promise<{ id: string }> {
    return (
      await httpClient.patch<DTO.UpdateItemResponse>(
        base + `/items/${encodeURIComponent(id)}`,
        updateItemToDto(value),
        { params: { locale } },
      )
    ).data;
  },
  async deleteItem(id: string): Promise<void> {
    await httpClient.delete(base + `/items/${encodeURIComponent(id)}`);
  },
  async uploadImage(
    id: string,
    locale: string,
    file: File,
    main: boolean,
  ): Promise<{ id: string; image_id: string; file_id: string }> {
    const body = new FormData();
    body.append("image", file);
    body.append("main", String(main));
    return (
      await httpClient.post<DTO.UploadImageResponse>(
        base +
          `/items/${encodeURIComponent(id)}/images/${encodeURIComponent(locale)}/upload`,
        body,
        { headers: { "Content-Type": undefined } },
      )
    ).data;
  },
  imageUrl(id: string, locale: string, imageId: string): string {
    return `/api${base}/items/${encodeURIComponent(id)}/images/${encodeURIComponent(locale)}/${encodeURIComponent(imageId)}/content`;
  },
  async defaultSchema(
    locale: string,
    signal?: AbortSignal,
  ): Promise<CatalogSchema> {
    const { data } = await httpClient.get<DTO.DefaultSchemaResponse>(
      base + "/product-type/default",
      { params: { locale }, signal },
    );
    return schemaFromDto(data);
  },
};
