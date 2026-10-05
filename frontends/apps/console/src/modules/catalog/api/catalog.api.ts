import { httpClient } from "@/app/providers/http";
import type {
  CreateProductDto,
  CreatedProductDto,
  ProductDto,
  PutContentDto,
  SavedContentDto,
  LocaleDto,
} from "./contracts";
export const catalogApi = {
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
