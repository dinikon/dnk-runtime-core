import { httpClient } from "@/app/providers/http";
import type {
  CreateProductDto,
  CreatedProductDto,
  ProductDto,
  PutContentDto,
  SavedContentDto,
  LocaleDto,
  ProductListItemDto,
  VariantStructureDto,
  ContentBlockDto,
  ProductTypeDto,
  CreateTypeDto,
  PutTypeDto,
  ContentBlockType,
} from "./contracts";
export const catalogApi = {
  async listProducts(locale: string, signal?: AbortSignal) {
    return (
      await httpClient.get<ProductListItemDto[]>("/console/catalog/products", {
        params: { locale },
        signal,
      })
    ).data;
  },
  async createVariableProduct(payload: {
    sku_ids: string[];
    contents: CreateProductDto["contents"];
    product_type_id?: string | null;
    schema_version?: number | null;
  }) {
    return (
      await httpClient.post<{ id: string; variant_ids: string[] }>(
        "/console/catalog/products/variable",
        payload,
      )
    ).data;
  },
  async deleteProduct(id: string) {
    await httpClient.delete(
      `/console/catalog/products/${encodeURIComponent(id)}`,
    );
  },
  async putVariantStructure(id: string, payload: VariantStructureDto) {
    return (
      await httpClient.put(
        `/console/catalog/products/${encodeURIComponent(id)}/variant-structure`,
        payload,
      )
    ).data;
  },
  async createVariant(id: string, sku_id: string) {
    return (
      await httpClient.post(
        `/console/catalog/products/${encodeURIComponent(id)}/variants`,
        { sku_id },
      )
    ).data;
  },
  async putVariant(id: string, variantId: string, sku_id: string) {
    return (
      await httpClient.put(
        `/console/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`,
        { sku_id },
      )
    ).data;
  },
  async deleteVariant(id: string, variantId: string) {
    await httpClient.delete(
      `/console/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`,
    );
  },
  async putVariantContent(
    id: string,
    variantId: string,
    locale: string,
    payload: PutContentDto,
  ) {
    return (
      await httpClient.put(
        `/console/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}/contents/${encodeURIComponent(locale)}`,
        payload,
      )
    ).data;
  },
  async createProduct(payload: CreateProductDto) {
    return (
      await httpClient.post<CreatedProductDto>(
        "/console/catalog/products",
        payload,
      )
    ).data;
  },
  async getProduct(id: string, locale: string, signal?: AbortSignal) {
    return (
      await httpClient.get<ProductDto>(
        `/console/catalog/products/${encodeURIComponent(id)}`,
        { params: { locale }, signal },
      )
    ).data;
  },
  async putProductContent(id: string, locale: string, payload: PutContentDto) {
    return (
      await httpClient.put<SavedContentDto>(
        `/console/catalog/products/${encodeURIComponent(id)}/contents/${encodeURIComponent(locale)}`,
        payload,
      )
    ).data;
  },
  async deleteProductContent(id: string, locale: string) {
    await httpClient.delete(`/console/catalog/products/${encodeURIComponent(id)}/contents/${encodeURIComponent(locale)}`);
  },
  async deleteVariantContent(id: string, variantId: string, locale: string) {
    await httpClient.delete(`/console/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}/contents/${encodeURIComponent(locale)}`);
  },
  async putProductType(id: string, product_type_id: string, expected_schema_version: number) {
    return (await httpClient.put(`/console/catalog/products/${encodeURIComponent(id)}/product-type`, { product_type_id, expected_schema_version })).data;
  },
  async listBlocks(signal?: AbortSignal) {
    return (await httpClient.get<ContentBlockDto[]>("/console/catalog/content-blocks", { signal })).data;
  },
  async getBlock(id: string, signal?: AbortSignal) {
    return (await httpClient.get<ContentBlockDto>(`/console/catalog/content-blocks/${encodeURIComponent(id)}`, { signal })).data;
  },
  async createBlock(payload: { code: string; type: ContentBlockType; translations: Record<string, string> }) {
    return (await httpClient.post<ContentBlockDto>("/console/catalog/content-blocks", payload)).data;
  },
  async putBlock(id: string, payload: { type: ContentBlockType; translations: Record<string, string> }) {
    return (await httpClient.put<ContentBlockDto>(`/console/catalog/content-blocks/${encodeURIComponent(id)}`, payload)).data;
  },
  async deleteBlock(id: string) {
    await httpClient.delete(`/console/catalog/content-blocks/${encodeURIComponent(id)}`);
  },
  async listProductTypes(signal?: AbortSignal) {
    return (await httpClient.get<ProductTypeDto[]>("/console/catalog/product-types", { signal })).data;
  },
  async getProductType(id: string, signal?: AbortSignal) {
    return (await httpClient.get<ProductTypeDto>(`/console/catalog/product-types/${encodeURIComponent(id)}`, { signal })).data;
  },
  async createProductType(payload: CreateTypeDto) {
    return (await httpClient.post<ProductTypeDto>("/console/catalog/product-types", payload)).data;
  },
  async putProductTypeSchema(id: string, payload: PutTypeDto) {
    return (await httpClient.put<ProductTypeDto>(`/console/catalog/product-types/${encodeURIComponent(id)}`, payload)).data;
  },
  async deleteProductType(id: string) {
    await httpClient.delete(`/console/catalog/product-types/${encodeURIComponent(id)}`);
  },
  async listLocales(signal?: AbortSignal) {
    return (
      await httpClient.get<LocaleDto[]>("/console/reference-data/locales", {
        signal,
      })
    ).data;
  },
};
