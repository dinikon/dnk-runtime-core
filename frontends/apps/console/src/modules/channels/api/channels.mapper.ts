import type { PublicationIdentitySummary } from "../model/publication-identity.types";
import type * as DTO from "./channels.dto";
import type {
  Platform,
  Channel,
  Connection,
  Initialization,
  Publication,
  CreateChannelInput,
  CreateConnectionInput,
  UpdateConnectionInput,
  ConnectionSaved,
  VerificationQueued,
  CreatedChannel,
  InitializationQueued,
} from "../model/channels.types";
export function mapChannel(dto: DTO.ChannelRowDto): Channel {
  return {
    id: dto.channel_id,
    name: dto.name,
    platformKind: dto.platform_kind,
    isEnabled: dto.is_enabled,
    isArchived: dto.is_archived,
    revision: dto.revision,
    connectionId: dto.connection_id,
    verificationStatus: dto.verification_status,
    isPaused: dto.is_paused,
  };
}
export function mapConnection(dto: DTO.GetConnectionResponseDto): Connection {
  return {
    channelId: dto.channel_id,
    id: dto.connection_id,
    revision: dto.revision,
    endpoint: dto.endpoint,
    settings: JSON.parse(JSON.stringify(dto.settings)),
    resourceIdentity: dto.resource_identity,
    verificationStatus: dto.verification_status,
    verificationJobId: dto.verification_job_id,
    generation: dto.generation,
    isPaused: dto.is_paused,
    credentialsPresent: dto.credentials_present,
    candidatePresent: dto.candidate_present,
    reasonCode: dto.reason_code,
    scopeLimitations: dto.scope_limitations,
  };
}
export function mapInitialization(
  dto: DTO.GetInitializationResponseDto,
): Initialization {
  return {
    runId: dto.run_id,
    connectionId: dto.connection_id,
    status: dto.status,
    processed: dto.processed,
    invalid: dto.invalid,
    sequence: dto.sequence,
    reasonCode: dto.reason_code,
    scopeLimitations: dto.scope_limitations,
    updatedAt: dto.updated_at,
    jobId: dto.job_id,
    readComplete: dto.read_complete,
    recoveryRequired: dto.recovery_required,
  };
}
export function mapPublication(dto: DTO.PublicationRowDto): Publication {
  return {
    identity: dto.identity
      ? {
          state: dto.identity.state,
          key: dto.identity.key,
          conflictCount: dto.identity.conflict_count,
        }
      : null,
    catalogItemId: dto.catalog_item_id,
    bindingId: dto.binding_id,
    representationId: dto.representation_id,
    representationRevision: dto.representation_revision,
    exportEnabled: dto.export_enabled ?? false,
    id: dto.publication_id,
    connectionId: dto.connection_id,
    resourceType: dto.resource_type,
    externalId: dto.external_id,
    externalSku: dto.external_sku,
    price: dto.price,
    salePrice: dto.sale_price,
    currency: dto.currency,
    quantity: dto.quantity,
    stockStatus: dto.stock_status,
    title: dto.title,
    titleLocale: dto.title_locale,
    mainImageUrl: dto.main_image_url,
    sourceUpdatedAt: dto.source_updated_at,
    warnings: dto.warnings,
    observedRevision: dto.observed_revision,
    firstSeenAt: dto.first_seen_at,
    lastSeenAt: dto.last_seen_at,
    lastImportRunId: dto.last_import_run_id,
  };
}

export function mapPlatform(dto: DTO.PlatformManifestDto): Platform {
  return {
    kind: dto.kind,
    label: dto.label,
    sdkVersion: dto.sdk_version,
    configVersion: dto.config_version,
    capabilities: dto.capabilities,
    credentialsSchema: dto.credentials_schema,
    endpointSchema: dto.endpoint_schema,
    settingsSchema: dto.settings_schema,
  };
}
export function createChannelPayload(
  input: CreateChannelInput,
): DTO.CreateChannelRequestDto {
  return { name: input.name.trim(), platform_kind: input.platformKind };
}
export function createConnectionPayload(
  input: CreateConnectionInput,
): DTO.CreateConnectionRequestDto {
  return {
    revision: input.revision,
    endpoint: input.settings.endpoint,
    settings: JSON.parse(JSON.stringify(input.settings.options)),
    credentials: { ...input.credentials },
  };
}
export function updateConnectionPayload(
  input: UpdateConnectionInput,
): DTO.UpdateConnectionRequestDto {
  return {
    revision: input.revision,
    endpoint: input.settings.endpoint,
    settings: JSON.parse(JSON.stringify(input.settings.options)),
    ...(input.credentials ? { credentials: { ...input.credentials } } : {}),
  };
}
export function mapCreatedChannel(
  dto: DTO.CreateChannelResponseDto,
): CreatedChannel {
  return {
    id: dto.channel_id,
    revision: dto.revision,
    isEnabled: dto.is_enabled,
  };
}
export function mapConnectionSaved(
  dto: DTO.CreateConnectionResponseDto | DTO.UpdateConnectionResponseDto,
): ConnectionSaved {
  return {
    channelId: dto.channel_id,
    connectionId: dto.connection_id,
    revision: dto.revision,
    verificationJobId: dto.verification_job_id,
  };
}
export function mapVerification(
  dto: DTO.VerifyConnectionResponseDto,
): VerificationQueued {
  return {
    channelId: dto.channel_id,
    revision: dto.revision,
    jobId: dto.job_id,
  };
}
export function mapInitializationQueued(
  dto: DTO.StartInitializationResponseDto,
): InitializationQueued {
  return { runId: dto.run_id, status: dto.status, jobId: dto.job_id };
}

export function mapIdentitySummary(
  dto: DTO.PublicationIdentitySummaryDto | null | undefined,
): PublicationIdentitySummary | null {
  if (!dto) return null;
  return {
    label: dto.label,
    total: dto.total,
    missing: dto.missing,
    duplicate: dto.duplicate,
    valid: dto.valid,
    duplicateGroups: dto.duplicate_groups,
    assessment: dto.assessment,
    checkedAt: dto.checked_at,
    scopeLimitations: [...dto.scope_limitations],
    helpTitle: dto.help_title,
    helpSteps: [...dto.help_steps],
    helpUrl: dto.help_url,
    recoveryVerified: dto.recovery_verified,
  };
}
