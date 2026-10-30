import { httpClient } from "@/app/providers/http";
import type { RepresentationPreview } from "../model/representation.types";
import type { PreviewRepresentationResponseDto } from "./representation.dto";
import { representationPreview } from "./representation.mapper";

export async function previewRepresentation(
  channelId: string,
  groupId: string,
  signal?: AbortSignal,
): Promise<RepresentationPreview> {
  const { data } = await httpClient.post<PreviewRepresentationResponseDto>(
    `/console/channels/${encodeURIComponent(channelId)}/catalog-bindings/${encodeURIComponent(groupId)}/representation/preview`,
    {},
    { signal },
  );
  return representationPreview(data);
}
