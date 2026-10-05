import { httpClient } from "@/app/providers/http";
import type {
  CategoryListDto,
  CategoryDto,
  CreateCategoryDto,
  CreatedCategoryDto,
  SavedCategoryContentDto,
  MovedCategoryDto,
  ProductCategoriesPayload,
  SavedProductCategoriesDto,
} from "./contracts";
const path = "/console/catalog/categories";
export const categoriesApi = {
  async list(locale: string, signal?: AbortSignal) {
    return (
      await httpClient.get<CategoryListDto[]>(path, {
        params: { locale },
        signal,
      })
    ).data;
  },
  async get(id: string, locale: string, signal?: AbortSignal) {
    return (
      await httpClient.get<CategoryDto>(`${path}/${encodeURIComponent(id)}`, {
        params: { locale },
        signal,
      })
    ).data;
  },
  async create(payload: CreateCategoryDto) {
    return (await httpClient.post<CreatedCategoryDto>(path, payload)).data;
  },
  async putContent(id: string, locale: string, name: string) {
    return (
      await httpClient.put<SavedCategoryContentDto>(
        `${path}/${encodeURIComponent(id)}/contents/${encodeURIComponent(locale)}`,
        { name },
      )
    ).data;
  },
  async move(id: string, parent_id: string | null) {
    return (
      await httpClient.put<MovedCategoryDto>(
        `${path}/${encodeURIComponent(id)}/parent`,
        { parent_id },
      )
    ).data;
  },
  async delete(id: string) {
    await httpClient.delete(`${path}/${encodeURIComponent(id)}`);
  },
  async putProductCategories(id: string, payload: ProductCategoriesPayload) {
    return (
      await httpClient.put<SavedProductCategoriesDto>(
        `/console/catalog/products/${encodeURIComponent(id)}/categories`,
        payload,
      )
    ).data;
  },
};
