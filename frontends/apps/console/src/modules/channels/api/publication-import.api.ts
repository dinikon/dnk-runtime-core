import { httpClient } from "@/app/providers/http";
import { normalizeApiError } from "./channels.error";
import { mapPublicationImport } from "./publication-import.mapper";
import type * as DTO from "./publication-import.dto";
import type * as Model from "../model/publication-import.types";
const path = (id: string): string =>
  `/console/channels/import-preparations/${encodeURIComponent(id)}`;
export const publicationImportApi = {
  async start(
    input: Model.StartPublicationImportInput,
    signal?: AbortSignal,
  ): Promise<string> {
    const payload: DTO.StartPublicationImportRequestDto = {
      preparation_id: input.preparationId,
      expected_observed_revision: input.observedRevision,
    };
    try {
      const { data } =
        await httpClient.post<DTO.StartPublicationImportResponseDto>(
          `/console/channels/publications/${encodeURIComponent(input.publicationId)}/import-preparations`,
          payload,
          { signal },
        );
      return data.preparation_id;
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async get(
    id: string,
    signal?: AbortSignal,
  ): Promise<Model.PublicationImport> {
    try {
      const { data } =
        await httpClient.get<DTO.GetPublicationImportResponseDto>(path(id), {
          signal,
        });
      const result = mapPublicationImport(data);
      return {
        ...result,
        images: result.images.map((image) => ({
          ...image,
          previewUrl: image.previewUrl
            ? httpClient.getUri({
                url: path(id) + "/image",
                params: { image_id: image.id },
              })
            : null,
        })),
      };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async retry(
    input: Model.ChangePublicationImportInput,
    signal?: AbortSignal,
  ): Promise<Model.ChangedPublicationImport> {
    const payload: DTO.RetryPublicationImportRequestDto = {
      expected_revision: input.revision,
    };
    try {
      const { data } =
        await httpClient.post<DTO.RetryPublicationImportResponseDto>(
          path(input.preparationId) + "/retry",
          payload,
          { signal },
        );
      return { preparationId: data.preparation_id, revision: data.revision };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async cancel(
    input: Model.ChangePublicationImportInput,
    signal?: AbortSignal,
  ): Promise<Model.ChangedPublicationImport> {
    const payload: DTO.CancelPublicationImportRequestDto = {
      expected_revision: input.revision,
    };
    try {
      const { data } =
        await httpClient.post<DTO.CancelPublicationImportResponseDto>(
          path(input.preparationId) + "/cancel",
          payload,
          { signal },
        );
      return { preparationId: data.preparation_id, revision: data.revision };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
};
