import { httpClient } from "@/app/providers/http";
import { schemaRequest } from "./feed-schema.api";
import type {
  ChangedPublicationOverrideDTO,
  PublicationFieldsDTO,
  SetPublicationOverrideDTO,
} from "./publication-fields.dto";
import {
  mapPublicationFields,
  overrideVersions,
} from "./publication-fields.mapper";
import type {
  PublicationFields,
  PublicationOverrideTarget,
  SetPublicationOverride,
} from "../model/publication-fields.types";

function publicationUrl(publicationId: string): string {
  return `/console/feed-builder/publications/${encodeURIComponent(publicationId)}`;
}
function overrideUrl(target: PublicationOverrideTarget): string {
  return `${publicationUrl(target.publicationId)}/overrides/${encodeURIComponent(target.fieldId)}`;
}

export const publicationFieldsApi = {
  get(publicationId: string, signal: AbortSignal): Promise<PublicationFields> {
    return schemaRequest(async () => {
      const response = await httpClient.get<PublicationFieldsDTO>(
        `${publicationUrl(publicationId)}/fields`,
        { signal },
      );
      return mapPublicationFields(response.data);
    });
  },
  set(input: SetPublicationOverride, signal: AbortSignal): Promise<number> {
    return schemaRequest(async () => {
      const payload: SetPublicationOverrideDTO = {
        ...overrideVersions(input),
        value: input.value,
      };
      const response = await httpClient.put<ChangedPublicationOverrideDTO>(
        overrideUrl(input),
        payload,
        { signal },
      );
      return response.data.publication_version;
    });
  },
  reset(
    input: PublicationOverrideTarget,
    signal: AbortSignal,
  ): Promise<number> {
    return schemaRequest(async () => {
      const response = await httpClient.delete<ChangedPublicationOverrideDTO>(
        overrideUrl(input),
        { signal, params: overrideVersions(input) },
      );
      return response.data.publication_version;
    });
  },
};
