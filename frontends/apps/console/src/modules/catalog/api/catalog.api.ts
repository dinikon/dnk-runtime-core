import { httpClient } from "@/app/providers/http";
import type * as DTO from "./catalog.dto";
const base = "/console/catalog";
export const catalogApi = {
  async locales(signal?: AbortSignal): Promise<DTO.LocaleDTO[]> {
    return (
      await httpClient.get<DTO.LocaleDTO[]>("/console/reference-data/locales", {
        signal,
      })
    ).data;
  },
  async createSimpleProduct(
    body: DTO.CreateSimpleProductRequest,
    signal?: AbortSignal,
  ): Promise<DTO.CreateSimpleProductResponse> {
    return (
      await httpClient.post<DTO.CreateSimpleProductResponse>(
        base + `/products/simple`,
        body,
        { signal },
      )
    ).data;
  },
  async changeProductType(
    product_id: string,
    body: DTO.ChangeProductTypeRequest,
    signal?: AbortSignal,
  ): Promise<DTO.ChangeProductTypeResponse> {
    return (
      await httpClient.put<DTO.ChangeProductTypeResponse>(
        base + `/products/${encodeURIComponent(product_id)}/type`,
        body,
        { signal },
      )
    ).data;
  },
  async setVariantProperties(
    product_id: string,
    variant_id: string,
    body: DTO.SetVariantPropertiesRequest,
    signal?: AbortSignal,
  ): Promise<DTO.SetVariantPropertiesResponse> {
    return (
      await httpClient.put<DTO.SetVariantPropertiesResponse>(
        base +
          `/products/${encodeURIComponent(product_id)}/variants/${encodeURIComponent(variant_id)}/properties`,
        body,
        { signal },
      )
    ).data;
  },
  async putProductContent(
    product_id: string,
    locale: string,
    body: DTO.PutProductContentRequest,
    signal?: AbortSignal,
  ): Promise<DTO.PutProductContentResponse> {
    return (
      await httpClient.put<DTO.PutProductContentResponse>(
        base +
          `/products/${encodeURIComponent(product_id)}/content/${encodeURIComponent(locale)}`,
        body,
        { signal },
      )
    ).data;
  },
  async deleteProductContent(
    product_id: string,
    locale: string,
    expectedRevision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await httpClient.delete(
      base +
        `/products/${encodeURIComponent(product_id)}/content/${encodeURIComponent(locale)}`,
      { signal, params: { expected_revision: expectedRevision } },
    );
  },
  async putVariantContent(
    product_id: string,
    variant_id: string,
    locale: string,
    body: DTO.PutVariantContentRequest,
    signal?: AbortSignal,
  ): Promise<DTO.PutVariantContentResponse> {
    return (
      await httpClient.put<DTO.PutVariantContentResponse>(
        base +
          `/products/${encodeURIComponent(product_id)}/variants/${encodeURIComponent(variant_id)}/content/${encodeURIComponent(locale)}`,
        body,
        { signal },
      )
    ).data;
  },
  async deleteVariantContent(
    product_id: string,
    variant_id: string,
    locale: string,
    expectedRevision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await httpClient.delete(
      base +
        `/products/${encodeURIComponent(product_id)}/variants/${encodeURIComponent(variant_id)}/content/${encodeURIComponent(locale)}`,
      { signal, params: { expected_revision: expectedRevision } },
    );
  },
  async deleteProduct(
    product_id: string,
    expectedRevision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await httpClient.delete(
      base + `/products/${encodeURIComponent(product_id)}`,
      { signal, params: { expected_revision: expectedRevision } },
    );
  },
  async createProductType(
    body: DTO.CreateProductTypeRequest,
    signal?: AbortSignal,
  ): Promise<DTO.CreateProductTypeResponse> {
    return (
      await httpClient.post<DTO.CreateProductTypeResponse>(
        base + `/product-types`,
        body,
        { signal },
      )
    ).data;
  },
  async deleteProductType(
    product_type_id: string,
    expectedRevision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await httpClient.delete(
      base + `/product-types/${encodeURIComponent(product_type_id)}`,
      { signal, params: { expected_revision: expectedRevision } },
    );
  },
  async putProductTypeTranslation(
    product_type_id: string,
    locale: string,
    body: DTO.PutProductTypeTranslationRequest,
    signal?: AbortSignal,
  ): Promise<DTO.PutProductTypeTranslationResponse> {
    return (
      await httpClient.put<DTO.PutProductTypeTranslationResponse>(
        base +
          `/product-types/${encodeURIComponent(product_type_id)}/translations/${encodeURIComponent(locale)}`,
        body,
        { signal },
      )
    ).data;
  },
  async replaceProductTypeSchema(
    product_type_id: string,
    body: DTO.ReplaceProductTypeSchemaRequest,
    signal?: AbortSignal,
  ): Promise<DTO.ReplaceProductTypeSchemaResponse> {
    return (
      await httpClient.put<DTO.ReplaceProductTypeSchemaResponse>(
        base + `/product-types/${encodeURIComponent(product_type_id)}/schema`,
        body,
        { signal },
      )
    ).data;
  },
  async createContentBlock(
    body: DTO.CreateContentBlockRequest,
    signal?: AbortSignal,
  ): Promise<DTO.CreateContentBlockResponse> {
    return (
      await httpClient.post<DTO.CreateContentBlockResponse>(
        base + `/content-blocks`,
        body,
        { signal },
      )
    ).data;
  },
  async deleteContentBlock(
    content_block_id: string,
    expectedRevision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await httpClient.delete(
      base + `/content-blocks/${encodeURIComponent(content_block_id)}`,
      { signal, params: { expected_revision: expectedRevision } },
    );
  },
  async updateContentBlock(
    content_block_id: string,
    body: DTO.UpdateContentBlockRequest,
    signal?: AbortSignal,
  ): Promise<DTO.UpdateContentBlockResponse> {
    return (
      await httpClient.put<DTO.UpdateContentBlockResponse>(
        base + `/content-blocks/${encodeURIComponent(content_block_id)}`,
        body,
        { signal },
      )
    ).data;
  },
  async getProduct(
    product_id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetProductResponse> {
    return (
      await httpClient.get<DTO.GetProductResponse>(
        base + `/products/${encodeURIComponent(product_id)}`,
        { signal, params: { locale } },
      )
    ).data;
  },
  async listProducts(
    locale: string,
    search = "",
    page = 1,
    pageSize = 20,
    typeId?: string,
    signal?: AbortSignal,
  ): Promise<DTO.ListProductsResponse> {
    return (
      await httpClient.get<DTO.ListProductsResponse>(base + `/products`, {
        signal,
        params: {
          locale,
          search,
          page,
          page_size: pageSize,
          product_type_id: typeId,
        },
      })
    ).data;
  },
  async getProductType(
    product_type_id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetProductTypeResponse> {
    return (
      await httpClient.get<DTO.GetProductTypeResponse>(
        base + `/product-types/${encodeURIComponent(product_type_id)}`,
        { signal, params: { locale } },
      )
    ).data;
  },
  async listProductTypes(
    locale: string,
    search = "",
    page = 1,
    pageSize = 20,
    signal?: AbortSignal,
  ): Promise<DTO.ListProductTypesResponse> {
    return (
      await httpClient.get<DTO.ListProductTypesResponse>(
        base + `/product-types`,
        { signal, params: { locale, search, page, page_size: pageSize } },
      )
    ).data;
  },
  async getContentBlock(
    content_block_id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetContentBlockResponse> {
    return (
      await httpClient.get<DTO.GetContentBlockResponse>(
        base + `/content-blocks/${encodeURIComponent(content_block_id)}`,
        { signal, params: { locale } },
      )
    ).data;
  },
  async listContentBlocks(
    locale: string,
    search = "",
    page = 1,
    pageSize = 20,
    signal?: AbortSignal,
  ): Promise<DTO.ListContentBlocksResponse> {
    return (
      await httpClient.get<DTO.ListContentBlocksResponse>(
        base + `/content-blocks`,
        { signal, params: { locale, search, page, page_size: pageSize } },
      )
    ).data;
  },
  async getVariant(
    product_id: string,
    variant_id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetVariantResponse> {
    return (
      await httpClient.get<DTO.GetVariantResponse>(
        base +
          `/products/${encodeURIComponent(product_id)}/variants/${encodeURIComponent(variant_id)}`,
        { signal, params: { locale } },
      )
    ).data;
  },
};
