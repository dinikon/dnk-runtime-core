import { httpClient } from "@/app/providers/http";
import { schemaRequest } from "./feed-schema.api";
import {
  mapPublication,
  mapPublications,
  addPublicationsPayload,
  mapAddedPublications,
  mapChangedPublication,
  mapVariantSelection,
} from "./feed-publication.mapper";
import type {
  ListPublicationsDTO,
  GetPublicationDTO,
  AddedPublicationsDTO,
  ChangedPublicationDTO,
  VariantSelectionDTO,
} from "./feed-publication.dto";
import type {
  PublicationPage,
  Publication,
  PublicationFilters,
  AddPublications,
  AddedPublications,
  ChangePublication,
  ChangedPublication,
  PublicationVersionAction,
  PublicationChoice,
} from "../model/feed-publication.types";
const root = "/console/feed-builder";
export const feedPublicationApi = {
  async list(
    feedId: string,
    filters: PublicationFilters,
    signal: AbortSignal,
  ): Promise<PublicationPage> {
    return schemaRequest(async () =>
      mapPublications(
        (
          await httpClient.get<ListPublicationsDTO>(
            `${root}/feeds/${encodeURIComponent(feedId)}/publications`,
            {
              signal,
              params: {
                ...filters,
                search: filters.search || undefined,
                status: filters.status || undefined,
              },
            },
          )
        ).data,
      ),
    );
  },
  async get(
    id: string,
    locale: string,
    signal: AbortSignal,
  ): Promise<Publication> {
    return schemaRequest(async () =>
      mapPublication(
        (
          await httpClient.get<GetPublicationDTO>(
            `${root}/publications/${encodeURIComponent(id)}`,
            { signal, params: { locale } },
          )
        ).data.publication,
      ),
    );
  },
  async add(
    value: AddPublications,
    signal: AbortSignal,
  ): Promise<AddedPublications> {
    return schemaRequest(async () =>
      mapAddedPublications(
        (
          await httpClient.post<AddedPublicationsDTO>(
            `${root}/feeds/${encodeURIComponent(value.feedId)}/publications`,
            addPublicationsPayload(value),
            { signal },
          )
        ).data,
      ),
    );
  },
  async change(
    value: ChangePublication,
    signal: AbortSignal,
  ): Promise<ChangedPublication> {
    return schemaRequest(async () =>
      mapChangedPublication(
        (
          await httpClient.patch<ChangedPublicationDTO>(
            `${root}/publications/${encodeURIComponent(value.id)}/status`,
            { expected_version: value.expectedVersion, status: value.status },
            { signal },
          )
        ).data,
      ),
    );
  },
  async archive(
    value: PublicationVersionAction,
    signal: AbortSignal,
  ): Promise<void> {
    return schemaRequest(async () => {
      await httpClient.delete(
        `${root}/publications/${encodeURIComponent(value.id)}`,
        { signal, params: { expected_version: value.expectedVersion } },
      );
    });
  },
  async restore(
    value: PublicationVersionAction,
    signal: AbortSignal,
  ): Promise<ChangedPublication> {
    return schemaRequest(async () =>
      mapChangedPublication(
        (
          await httpClient.post<ChangedPublicationDTO>(
            `${root}/publications/${encodeURIComponent(value.id)}/restore`,
            { expected_version: value.expectedVersion },
            { signal },
          )
        ).data,
      ),
    );
  },
  async variants(
    feedId: string,
    itemId: string,
    locale: string,
    signal: AbortSignal,
  ): Promise<PublicationChoice[]> {
    return schemaRequest(async () =>
      mapVariantSelection(
        (
          await httpClient.get<VariantSelectionDTO>(
            `${root}/feeds/${encodeURIComponent(feedId)}/variant-selection/${encodeURIComponent(itemId)}`,
            { signal, params: { locale } },
          )
        ).data,
      ),
    );
  },
};
