import type {
  GetContentUpdateResponseDto,
  ListContentUpdatesResponseDto,
  StartContentUpdateRequestDto,
  ConfirmContentUpdateRequestDto,
} from "./content-updates.dto";
import type {
  ContentUpdate,
  ContentUpdateSummary,
  StartContentUpdateInput,
  ConfirmContentUpdateInput,
} from "../model/content-update.types";
export function mapContentUpdate(
  dto: GetContentUpdateResponseDto,
): ContentUpdate {
  return {
    id: dto.id,
    channelId: dto.channel_id,
    status: dto.status,
    revision: dto.revision,
    sequence: dto.sequence,
    previewHash: dto.preview_hash,
    createdAt: dto.created_at,
    expiresAt: dto.expires_at,
    confirmedAt: dto.confirmed_at,
    outboundEnabled: dto.outbound_enabled,
    interrupted: dto.interrupted,
    items: dto.items.map((item) => ({
      publicationId: item.publication_id,
      catalogItemId: item.catalog_item_id,
      externalId: item.external_id,
      desired: item.desired.map((text) => ({ ...text })),
      observed: item.observed.map((text) => ({ ...text })),
      status: item.status,
      issues: [...item.issues],
      attempts: item.attempts,
    })),
  };
}
export function mapContentUpdateHistory(
  dto: ListContentUpdatesResponseDto,
): ContentUpdateSummary[] {
  return dto.items.map((item) => ({
    id: item.id,
    status: item.status,
    createdAt: item.created_at,
    total: item.total,
  }));
}
export function contentUpdateStartPayload(
  input: StartContentUpdateInput,
): StartContentUpdateRequestDto {
  return {
    run_id: input.runId,
    publication_ids: [...input.publicationIds].sort(),
  };
}
export function contentUpdateConfirmPayload(
  input: ConfirmContentUpdateInput,
): ConfirmContentUpdateRequestDto {
  return { expected_revision: input.revision, preview_hash: input.previewHash };
}
