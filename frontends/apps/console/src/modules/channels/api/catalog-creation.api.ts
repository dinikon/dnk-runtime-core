import { httpClient } from "@/app/providers/http";
import type { CreatePublicationCatalogResponse } from "./catalog-creation.dto";
import type { CreatePublicationCatalogResult } from "../model/catalog-creation.types";
import { publicationCatalogFromDto } from "./catalog-creation.mapper";
export async function createPublicationCatalog(
  channelId: string,
  publicationId: string,
): Promise<CreatePublicationCatalogResult> {
  const { data } = await httpClient.post<CreatePublicationCatalogResponse>(
    `/console/channels/${encodeURIComponent(channelId)}/publications/${encodeURIComponent(publicationId)}/catalog-item`,
    undefined,
    { timeout: 120000 },
  );
  return publicationCatalogFromDto(data);
}
