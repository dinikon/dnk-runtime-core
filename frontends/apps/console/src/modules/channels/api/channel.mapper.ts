import type {
  ChannelDto,
  PlatformDto,
  SavedChannelDto,
  CreateChannelDto,
  UpdateChannelDto,
} from "./channel.dto";
import type {
  Channel,
  Platform,
  ChannelSaved,
  ChannelSave,
} from "../model/channel.types";
export function mapChannel(v: ChannelDto): Channel {
  return {
    id: v.id,
    name: v.name,
    platformKind: v.platform_kind,
    revision: v.revision,
    config: v.config,
    configRevision: v.config_revision,
    identity: v.identity,
    verification: {
      jobId: v.verification.job_id,
      configRevision: v.verification.config_revision,
      status: v.verification.status,
      checkedAt: v.verification.checked_at,
      errorCode: v.verification.error_code,
    },
    recoveryRequired: v.recovery_required,
    availableCapabilities: v.available_capabilities,
    createdAt: v.created_at,
    updatedAt: v.updated_at,
  };
}
export function mapPlatform(v: PlatformDto): Platform {
  return {
    kind: v.kind,
    title: v.title,
    configVersion: v.config_version,
    configSchema: v.config_schema,
    credentialsSchema: v.credentials_schema,
    supportedCapabilities: v.supported_capabilities,
  };
}
export function mapSaved(v: SavedChannelDto): ChannelSaved {
  return {
    id: v.id,
    revision: v.revision,
    verificationJobId: v.verification_job_id,
  };
}
export function createPayload(v: ChannelSave): CreateChannelDto {
  if (!v.credentials) throw new Error("Credentials required");
  return {
    name: v.name,
    platform_kind: v.platformKind,
    config: v.config,
    credentials: v.credentials,
  };
}
export function updatePayload(
  v: ChannelSave,
  revision: number,
): UpdateChannelDto {
  return {
    name: v.name,
    config: v.config,
    expected_revision: revision,
    ...(v.credentials ? { credentials: v.credentials } : {}),
  };
}
