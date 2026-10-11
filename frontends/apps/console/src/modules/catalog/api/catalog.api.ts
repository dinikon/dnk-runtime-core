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
  async listItems(
    locale: string,
    search = "",
    offset = 0,
    limit = 20,
    kind?: DTO.ItemKind,
    status?: DTO.ItemStatus,
    signal?: AbortSignal,
  ): Promise<DTO.ListItemsResponse> {
    return (
      await httpClient.get<DTO.ListItemsResponse>(base + "/items", {
        params: { locale, search, offset, limit, kind, status },
        signal,
      })
    ).data;
  },
  async getItem(
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<DTO.GetItemResponse> {
    return (
      await httpClient.get<DTO.GetItemResponse>(
        base + `/items/${encodeURIComponent(id)}`,
        { params: { locale }, signal },
      )
    ).data;
  },
  async listVariants(
    id: string,
    locale: string,
    offset = 0,
    limit = 100,
    signal?: AbortSignal,
  ): Promise<DTO.ListVariantsResponse> {
    return (
      await httpClient.get<DTO.ListVariantsResponse>(
        base + `/items/${encodeURIComponent(id)}/variants`,
        { params: { locale, offset, limit }, signal },
      )
    ).data;
  },
  async createSimple(virtual = false): Promise<DTO.CreateItemResponse> {
    return (
      await httpClient.post<DTO.CreateItemResponse>(base + "/items/simple", {
        virtual,
      })
    ).data;
  },
  async createVariable(
    structure: DTO.StructureDTO,
  ): Promise<DTO.CreateItemResponse> {
    return (
      await httpClient.post<DTO.CreateItemResponse>(base + "/items/variable", {
        structure,
      })
    ).data;
  },
  async saveItem(
    id: string,
    section: DTO.ItemSection,
    expectedRootRevision: number,
    value: Record<string, unknown>,
    locale: string,
  ): Promise<DTO.MutationResponse> {
    const localized = ["content", "galleries"].includes(section);
    return (
      await httpClient.put<DTO.MutationResponse>(
        base +
          `/items/${encodeURIComponent(id)}/${section === "galleries" ? "gallery" : section}` +
          (localized ? `/${encodeURIComponent(locale)}` : ""),
        { expected_root_revision: expectedRootRevision, ...value },
      )
    ).data;
  },
  async deleteItem(
    id: string,
    revision: number,
    discardedIds: string[] = [],
  ): Promise<void> {
    await httpClient.delete(base + `/items/${encodeURIComponent(id)}`, {
      params: { expected_root_revision: revision, discarded_ids: discardedIds },
      paramsSerializer: { indexes: null },
    });
  },
  async inheritSection(
    id: string,
    section: "content" | "galleries",
    locale: string,
    revision: number,
  ): Promise<void> {
    await httpClient.delete(
      base +
        `/items/${encodeURIComponent(id)}/${section === "galleries" ? "gallery" : section}/${encodeURIComponent(locale)}`,
      { params: { expected_root_revision: revision } },
    );
  },
  async uploadImage(
    id: string,
    locale: string,
    revision: number,
    file: File,
    main: boolean,
  ): Promise<DTO.MutationResponse> {
    const body = new FormData();
    body.append("image", file);
    body.append("expected_root_revision", String(revision));
    body.append("main", String(main));
    return (
      await httpClient.post<DTO.MutationResponse>(
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
  ): Promise<DTO.DefaultSchemaResponse> {
    return (
      await httpClient.get<DTO.DefaultSchemaResponse>(
        base + "/product-type/default",
        { params: { locale }, signal },
      )
    ).data;
  },
};
