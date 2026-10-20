import { httpClient } from "@/app/providers/http";
import { normalizeApiError } from "./channels.error";
import type * as DTO from "./catalog-links.dto";
import type * as Model from "../model/catalog-links.types";
import {
  mapCandidate,
  mapPreview,
  mapCreatedDraft,
  mapBound,
  createDraftPayload,
} from "./catalog-links.mapper";
const path = (id: string): string =>
  `/console/channels/publications/${encodeURIComponent(id)}`;
export const catalogLinksApi = {
  async candidates(
    input: Model.CatalogCandidatesInput,
    signal?: AbortSignal,
  ): Promise<Model.CatalogCandidatesPage> {
    try {
      const { data } =
        await httpClient.get<DTO.ListCatalogCandidatesResponseDto>(
          path(input.publicationId) + "/catalog-candidates",
          {
            signal,
            params: {
              locale: input.locale,
              search: input.search || undefined,
              offset: input.offset,
              limit: input.limit,
            },
          },
        );
      return {
        publicationId: input.publicationId,
        locale: input.locale,
        items: data.items.map(mapCandidate),
        total: data.total,
      };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async preview(
    input: Model.DraftPreviewInput,
    signal?: AbortSignal,
  ): Promise<Model.DraftPreview> {
    try {
      const { data } = await httpClient.get<DTO.PreviewCatalogDraftResponseDto>(
        path(input.publicationId) + "/catalog-draft-preview",
        {
          signal,
          params: {
            locale: input.locale,
            expected_observed_revision: input.observedRevision,
          },
        },
      );
      return mapPreview(data, input.publicationId, input.locale);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async source(
    id: string,
    signal?: AbortSignal,
  ): Promise<Model.PublicationSnapshot> {
    try {
      const { data } =
        await httpClient.get<DTO.GetPublicationSnapshotResponseDto>(path(id), {
          signal,
        });
      return {
        id: data.publication_id,
        observedRevision: data.observed_revision,
        titleLocale: data.title_locale,
      };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async bind(
    input: Model.BindPublicationInput,
    signal?: AbortSignal,
  ): Promise<Model.BoundPublication> {
    try {
      const payload: DTO.BindPublicationRequestDto = {
        catalog_item_id: input.catalogItemId,
        expected_revision: input.expectedRevision,
      };
      const { data } = await httpClient.post<DTO.BindPublicationResponseDto>(
        path(input.publicationId) + "/binding",
        payload,
        { signal },
      );
      return mapBound(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async unbind(
    input: Model.UnbindPublicationInput,
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      const payload: DTO.UnbindPublicationRequestDto = {
        binding_id: input.bindingId,
        expected_revision: input.expectedRevision,
      };
      await httpClient.delete(path(input.publicationId) + "/binding", {
        data: payload,
        signal,
      });
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async createDraft(
    input: Model.CreateDraftInput,
    signal?: AbortSignal,
  ): Promise<Model.CreatedCatalogDraft> {
    try {
      const { data } = await httpClient.post<DTO.CreateCatalogDraftResponseDto>(
        path(input.publicationId) + "/catalog-item",
        createDraftPayload(input),
        { signal },
      );
      return mapCreatedDraft(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
};
