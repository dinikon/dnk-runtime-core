import { httpClient } from "@/app/providers/http";
import type * as DTO from "./catalog.dto";
const base = "/console/catalog";
export const catalogApi = {
  async createCategory(
    body: DTO.CreateCategoryRequest,
  ): Promise<DTO.CreateCategoryResponse> {
    return (
      await httpClient.post<DTO.CreateCategoryResponse>(
        base + "/categories",
        body,
      )
    ).data;
  },
  async putCategoryContent(
    id: string,
    locale: string,
    body: DTO.PutCategoryContentRequest,
  ): Promise<DTO.PutCategoryContentResponse> {
    return (
      await httpClient.put<DTO.PutCategoryContentResponse>(
        base +
          `/categories/${encodeURIComponent(id)}/translations/${encodeURIComponent(locale)}`,
        body,
      )
    ).data;
  },
  async getCategory(
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetCategoryResponse> {
    return (
      await httpClient.get<DTO.GetCategoryResponse>(
        base + `/categories/${encodeURIComponent(id)}`,
        { params: { locale }, signal },
      )
    ).data;
  },
  async deleteCategory(id: string, revision: number): Promise<void> {
    await httpClient.delete(base + `/categories/${encodeURIComponent(id)}`, {
      params: { expected_revision: revision },
    });
  },
  async listCategories(
    locale: string,
    search = "",
    page = 1,
    page_size = 20,
    signal?: AbortSignal,
    parentId?: string,
    rootsOnly = false,
  ): Promise<DTO.ListCategoriesResponse> {
    return (
      await httpClient.get<DTO.ListCategoriesResponse>(base + "/categories", {
        params: {
          locale,
          search,
          page,
          page_size,
          parent_id: parentId,
          roots_only: rootsOnly,
        },
        signal,
      })
    ).data;
  },
  async createTag(body: DTO.CreateTagRequest): Promise<DTO.CreateTagResponse> {
    return (await httpClient.post<DTO.CreateTagResponse>(base + "/tags", body))
      .data;
  },
  async putTagTranslation(
    id: string,
    locale: string,
    body: DTO.PutTagTranslationRequest,
  ): Promise<DTO.PutTagTranslationResponse> {
    return (
      await httpClient.put<DTO.PutTagTranslationResponse>(
        base +
          `/tags/${encodeURIComponent(id)}/translations/${encodeURIComponent(locale)}`,
        body,
      )
    ).data;
  },
  async getTag(
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetTagResponse> {
    return (
      await httpClient.get<DTO.GetTagResponse>(
        base + `/tags/${encodeURIComponent(id)}`,
        { params: { locale }, signal },
      )
    ).data;
  },
  async deleteTag(id: string, revision: number): Promise<void> {
    await httpClient.delete(base + `/tags/${encodeURIComponent(id)}`, {
      params: { expected_revision: revision },
    });
  },
  async listTags(
    locale: string,
    search = "",
    page = 1,
    page_size = 20,
    signal?: AbortSignal,
  ): Promise<DTO.ListTagsResponse> {
    return (
      await httpClient.get<DTO.ListTagsResponse>(base + "/tags", {
        params: { locale, search, page, page_size },
        signal,
      })
    ).data;
  },
  async moveCategory(
    id: string,
    body: DTO.MoveCategoryRequest,
  ): Promise<DTO.MoveCategoryResponse> {
    return (
      await httpClient.put<DTO.MoveCategoryResponse>(
        base + `/categories/${encodeURIComponent(id)}/parent`,
        body,
      )
    ).data;
  },
  async setProductAttributes(
    id: string,
    body: DTO.SetProductAttributesRequest,
  ): Promise<DTO.SetProductAttributesResponse> {
    return (
      await httpClient.put<DTO.SetProductAttributesResponse>(
        base + `/products/${encodeURIComponent(id)}/attributes`,
        body,
      )
    ).data;
  },
  async setProductCategories(
    id: string,
    body: DTO.SetProductCategoriesRequest,
  ): Promise<DTO.SetProductCategoriesResponse> {
    return (
      await httpClient.put<DTO.SetProductCategoriesResponse>(
        base + `/products/${encodeURIComponent(id)}/categories`,
        body,
      )
    ).data;
  },
  async setProductTags(
    id: string,
    body: DTO.SetProductTagsRequest,
  ): Promise<DTO.SetProductTagsResponse> {
    return (
      await httpClient.put<DTO.SetProductTagsResponse>(
        base + `/products/${encodeURIComponent(id)}/tags`,
        body,
      )
    ).data;
  },

  async createVariableProduct(
    body: DTO.CreateVariableProductRequest,
  ): Promise<DTO.CreateVariableProductResponse> {
    return (
      await httpClient.post<DTO.CreateVariableProductResponse>(
        base + "/products/variable",
        body,
      )
    ).data;
  },
  async replaceVariants(
    id: string,
    body: DTO.ReplaceVariantsRequest,
  ): Promise<DTO.ReplaceVariantsResponse> {
    return (
      await httpClient.put<DTO.ReplaceVariantsResponse>(
        base + `/products/${encodeURIComponent(id)}/structure`,
        body,
      )
    ).data;
  },
  async changeProductKind(
    id: string,
    body: DTO.ChangeProductKindRequest,
  ): Promise<DTO.ChangeProductKindResponse> {
    return (
      await httpClient.put<DTO.ChangeProductKindResponse>(
        base + `/products/${encodeURIComponent(id)}/kind`,
        body,
      )
    ).data;
  },
  async createAttribute(
    body: DTO.CreateAttributeRequest,
  ): Promise<DTO.CreateAttributeResponse> {
    return (
      await httpClient.post<DTO.CreateAttributeResponse>(
        base + "/attributes",
        body,
      )
    ).data;
  },
  async putAttributeTranslation(
    id: string,
    locale: string,
    body: DTO.PutAttributeTranslationRequest,
  ): Promise<DTO.PutAttributeTranslationResponse> {
    return (
      await httpClient.put<DTO.PutAttributeTranslationResponse>(
        base +
          `/attributes/${encodeURIComponent(id)}/translations/${encodeURIComponent(locale)}`,
        body,
      )
    ).data;
  },
  async replaceAttributeOptions(
    id: string,
    locale: string,
    body: DTO.ReplaceAttributeOptionsRequest,
  ): Promise<DTO.ReplaceAttributeOptionsResponse> {
    return (
      await httpClient.put<DTO.ReplaceAttributeOptionsResponse>(
        base +
          `/attributes/${encodeURIComponent(id)}/options/${encodeURIComponent(locale)}`,
        body,
      )
    ).data;
  },
  async deleteAttribute(id: string, revision: number): Promise<void> {
    await httpClient.delete(base + `/attributes/${encodeURIComponent(id)}`, {
      params: { expected_revision: revision },
    });
  },
  async getAttribute(
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetAttributeResponse> {
    return (
      await httpClient.get<DTO.GetAttributeResponse>(
        base + `/attributes/${encodeURIComponent(id)}`,
        { params: { locale }, signal },
      )
    ).data;
  },
  async listAttributes(
    locale: string,
    search = "",
    page = 1,
    page_size = 20,
    signal?: AbortSignal,
  ): Promise<DTO.ListAttributesResponse> {
    return (
      await httpClient.get<DTO.ListAttributesResponse>(base + "/attributes", {
        params: { locale, search, page, page_size },
        signal,
      })
    ).data;
  },

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
    kind?: "simple" | "variable",
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
          kind,
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
