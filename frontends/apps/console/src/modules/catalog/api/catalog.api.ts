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
    short_description: string,
  ) {
    return (
      await httpClient.put(
        `/console/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}/contents/${encodeURIComponent(locale)}`,
        { short_description },
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
  async listLocales(signal?: AbortSignal) {
    return (
      await httpClient.get<LocaleDto[]>("/console/reference-data/locales", {
        signal,
      })
    ).data;
  },
};
