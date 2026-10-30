import { httpClient } from "@/app/providers/http";
import type {
  RepresentationPreview,
  RepresentationDetails,
  RepresentationDraftInput,
  SaveRepresentationInput,
  RepresentationWriteInput,
} from "../model/representation.types";
import type {
  PreviewRepresentationResponseDto,
  GetRepresentationResponseDto,
  SaveRepresentationResponseDto,
  EnableRepresentationResponseDto,
  DisableRepresentationResponseDto,
} from "./representation.dto";
import {
  representationPreview,
  representationDetails,
  representationDraftPayload,
  representationVersionPayload,
} from "./representation.mapper";

const path = (channelId: string, groupId: string): string =>
  `/console/channels/${encodeURIComponent(channelId)}/catalog-bindings/${encodeURIComponent(groupId)}/representation`;

export async function previewRepresentation(
  channelId: string,
  groupId: string,
  signal?: AbortSignal,
  draft?: RepresentationDraftInput,
): Promise<RepresentationPreview> {
  const { data } = await httpClient.post<PreviewRepresentationResponseDto>(
    `${path(channelId, groupId)}/preview`,
    draft ? representationDraftPayload(draft) : {},
    { signal },
  );
  return representationPreview(data);
}

export async function getRepresentation(
  channelId: string,
  groupId: string,
  signal?: AbortSignal,
): Promise<RepresentationDetails> {
  const { data } = await httpClient.get<GetRepresentationResponseDto>(
    path(channelId, groupId),
    { signal },
  );
  return representationDetails(data);
}
export async function saveRepresentation(
  input: SaveRepresentationInput,
): Promise<RepresentationDetails> {
  const { data } = await httpClient.put<SaveRepresentationResponseDto>(
    path(input.channelId, input.groupId),
    representationDraftPayload(input),
  );
  return representationDetails(data);
}
export async function enableRepresentationExport(
  input: RepresentationWriteInput,
): Promise<RepresentationDetails> {
  const { data } = await httpClient.post<EnableRepresentationResponseDto>(
    `${path(input.channelId, input.groupId)}/enable`,
    representationVersionPayload(input),
  );
  return representationDetails(data);
}
export async function disableRepresentationExport(
  input: RepresentationWriteInput,
): Promise<RepresentationDetails> {
  const { data } = await httpClient.post<DisableRepresentationResponseDto>(
    `${path(input.channelId, input.groupId)}/disable`,
    representationVersionPayload(input),
  );
  return representationDetails(data);
}
