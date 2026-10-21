import type {
  PublicationIdentity,
  PublicationIdentitySummary,
} from "./publication-identity.types";
export interface StringFieldSchema {
  type?: string;
  title?: string;
  description?: string;
  format?: string;
  minLength?: number;
  maxLength?: number;
  default?: string;
  const?: string;
  writeOnly?: boolean;
}
export interface CredentialsSchema {
  type?: string;
  properties?: Record<string, StringFieldSchema>;
  required?: string[];
  additionalProperties?: boolean;
}
export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type SettingsObject = { [key: string]: JsonValue };
export interface SettingsSchema {
  type?: string;
  title?: string;
  description?: string;
  properties?: Record<string, SettingsSchema>;
  required?: string[];
  additionalProperties?: boolean;
  items?: SettingsSchema;
  prefixItems?: SettingsSchema[];
  minItems?: number;
  maxItems?: number;
  uniqueItems?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  enum?: JsonValue[];
  const?: JsonValue;
  default?: JsonValue;
  "x-reference"?: "locale" | "currency";
}
export interface Platform {
  kind: string;
  label: string;
  sdkVersion: number;
  configVersion: number;
  capabilities: string[];
  credentialsSchema: CredentialsSchema;
  endpointSchema: StringFieldSchema;
  settingsSchema: SettingsSchema;
}
export interface Channel {
  id: string;
  name: string;
  platformKind: string;
  isEnabled: boolean;
  isArchived: boolean;
  revision: number;
  connectionId: string | null;
  verificationStatus: string | null;
  isPaused: boolean | null;
}
export interface Connection {
  channelId: string;
  id: string;
  revision: number;
  endpoint: string;
  settings: SettingsObject;
  resourceIdentity: string | null;
  verificationStatus: string;
  verificationJobId: string | null;
  generation: number;
  isPaused: boolean;
  credentialsPresent: boolean;
  candidatePresent: boolean;
  reasonCode: string | null;
  scopeLimitations: string[];
}
export interface Initialization {
  runId: string | null;
  connectionId: string;
  status: string;
  processed: number;
  invalid: number;
  sequence: number;
  reasonCode: string | null;
  scopeLimitations: string[];
  updatedAt: string | null;
  jobId: string | null;
  readComplete: boolean;
  recoveryRequired: boolean;
}
export interface Publication {
  identity: PublicationIdentity | null;
  catalogItemId: string | null;
  bindingId: string | null;
  representationId: string | null;
  representationRevision: number | null;
  exportEnabled: boolean;
  id: string;
  connectionId: string;
  resourceType: string;
  externalId: string;
  externalSku: string | null;
  price: string | null;
  salePrice: string | null;
  currency: string | null;
  quantity: string | null;
  stockStatus: string;
  title: string | null;
  titleLocale: string | null;
  mainImageUrl: string | null;
  sourceUpdatedAt: string | null;
  warnings: string[];
  observedRevision: number;
  firstSeenAt: string;
  lastSeenAt: string;
  lastImportRunId: string;
}
export interface ChannelsPage {
  items: Channel[];
  total: number;
}
export interface PublicationsPage {
  identitySummary: PublicationIdentitySummary | null;
  items: Publication[];
  total: number;
}
export interface ReferenceOption {
  code: string;
  name: string;
}
export interface ConnectionReferences {
  locales: ReferenceOption[];
  currencies: ReferenceOption[];
}
export interface CreateChannelInput {
  name: string;
  platformKind: string;
}
export interface CreatedChannel {
  id: string;
  revision: number;
  isEnabled: boolean;
}
export interface ConnectionSettings {
  endpoint: string;
  options: SettingsObject;
}
export interface CreateConnectionInput {
  channelId: string;
  revision: number;
  settings: ConnectionSettings;
  credentials: Record<string, string>;
}
export interface UpdateConnectionInput {
  channelId: string;
  revision: number;
  settings: ConnectionSettings;
  credentials?: Record<string, string>;
}
export interface ConnectionSaved {
  channelId: string;
  connectionId: string;
  revision: number;
  verificationJobId: string | null;
}
export interface ChannelRevisionInput {
  channelId: string;
  revision: number;
}
export interface VerificationQueued {
  channelId: string;
  revision: number;
  jobId: string;
}
export interface StartInitializationInput {
  connectionId: string;
  requestKey: string;
}
export interface InitializationQueued {
  runId: string;
  status: string;
  jobId: string | null;
}
export interface ChannelsFilters {
  offset: number;
  limit: number;
}
export interface PublicationsFilters extends ChannelsFilters {
  exportStatus?: string;
  identityStatus?: string;
  identityKey?: string;
  search: string;
  stockStatus: string;
  bindingStatus?: string;
}
export interface ConnectionFormValues {
  endpoint: string;
  settings: SettingsObject;
  replaceCredentials: boolean;
  credentials: Record<string, string>;
}
