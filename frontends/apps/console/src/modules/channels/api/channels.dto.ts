import type {
  PublicationIdentityState,
  PublicationIdentitySummary,
} from "../model/publication-identity.types";
export interface PublicationIdentityDto {
  state: PublicationIdentityState;
  key: string | null;
  conflict_count: number;
}
export interface PublicationIdentitySummaryDto {
  label: string;
  total: number;
  missing: number;
  duplicate: number;
  valid: number;
  duplicate_groups: number;
  assessment: PublicationIdentitySummary["assessment"];
  checked_at: string | null;
  scope_limitations: string[];
  help_title: string;
  help_steps: string[];
  help_url: string;
  recovery_verified: boolean;
}
import type {
  CredentialsSchema,
  StringFieldSchema,
  SettingsObject,
  SettingsSchema,
} from "../model/channels.types";
export interface ChannelRowDto {
  channel_id: string;
  name: string;
  platform_kind: string;
  is_enabled: boolean;
  is_archived: boolean;
  revision: number;
  connection_id: string | null;
  verification_status: string | null;
  is_paused: boolean | null;
}
export interface GetConnectionResponseDto {
  channel_id: string;
  connection_id: string;
  revision: number;
  endpoint: string;
  settings: SettingsObject;
  resource_identity: string | null;
  verification_status: string;
  verification_job_id: string | null;
  generation: number;
  is_paused: boolean;
  credentials_present: boolean;
  candidate_present: boolean;
  reason_code: string | null;
  scope_limitations: string[];
}
export interface GetInitializationResponseDto {
  run_id: string | null;
  connection_id: string;
  status: string;
  processed: number;
  invalid: number;
  sequence: number;
  reason_code: string | null;
  scope_limitations: string[];
  updated_at: string | null;
  job_id: string | null;
  read_complete: boolean;
  recovery_required: boolean;
}
export interface PublicationRowDto {
  identity?: PublicationIdentityDto | null;
  catalog_item_id: string | null;
  binding_id: string | null;
  representation_id: string | null;
  representation_revision: number | null;
  publication_id: string;
  connection_id: string;
  resource_type: string;
  external_id: string;
  external_sku: string | null;
  price: string | null;
  sale_price: string | null;
  currency: string | null;
  quantity: string | null;
  stock_status: string;
  title: string | null;
  title_locale: string | null;
  main_image_url: string | null;
  source_updated_at: string | null;
  warnings: string[];
  observed_revision: number;
  first_seen_at: string;
  last_seen_at: string;
  last_import_run_id: string;
}

export interface PlatformManifestDto {
  kind: string;
  label: string;
  sdk_version: number;
  config_version: number;
  capabilities: string[];
  credentials_schema: CredentialsSchema;
  endpoint_schema: StringFieldSchema;
  settings_schema: SettingsSchema;
}
export interface ListPlatformsResponseDto {
  items: PlatformManifestDto[];
}
export interface GetPlatformConfigResponseDto {
  manifest: PlatformManifestDto;
}
export interface ListChannelsResponseDto {
  items: ChannelRowDto[];
  total: number;
}
export interface GetChannelResponseDto {
  channel_id: string;
  name: string;
  platform_kind: string;
  is_enabled: boolean;
  is_archived: boolean;
  revision: number;
  connection_id: string | null;
  verification_status: string | null;
  is_paused: boolean | null;
}
export interface ListPublicationsResponseDto {
  identity_summary?: PublicationIdentitySummaryDto | null;
  items: PublicationRowDto[];
  total: number;
}
export interface CreateChannelRequestDto {
  name: string;
  platform_kind: string;
}
export interface CreateChannelResponseDto {
  channel_id: string;
  revision: number;
  is_enabled: boolean;
}
export interface CreateConnectionRequestDto {
  revision: number;
  endpoint: string;
  settings: SettingsObject;
  credentials: Record<string, string>;
}
export interface CreateConnectionResponseDto {
  channel_id: string;
  connection_id: string;
  revision: number;
  verification_job_id: string;
}
export interface UpdateConnectionRequestDto {
  revision: number;
  endpoint: string;
  settings: SettingsObject;
  credentials?: Record<string, string>;
}
export interface UpdateConnectionResponseDto {
  channel_id: string;
  connection_id: string;
  revision: number;
  verification_job_id: string | null;
}
export interface VerifyConnectionRequestDto {
  revision: number;
}
export interface VerifyConnectionResponseDto {
  channel_id: string;
  revision: number;
  job_id: string;
}
export interface PauseConnectionRequestDto {
  revision: number;
}
export interface ResumeConnectionRequestDto {
  revision: number;
}
export interface StartInitializationRequestDto {
  request_key: string;
}
export interface StartInitializationResponseDto {
  run_id: string;
  status: string;
  job_id: string | null;
}
export interface ReferenceOptionDto {
  code: string;
  name: string;
}
