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
export interface Platform {
  kind: string;
  label: string;
  sdkVersion: number;
  configVersion: number;
  capabilities: string[];
  credentialsSchema: CredentialsSchema;
  endpointSchema: StringFieldSchema;
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
  locales: string[];
  currency: string | null;
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
  id: string;
  coreVersion: number;
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
  locales: string[];
  currency: string | null;
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
  search: string;
  stockStatus: string;
}
export interface ConnectionFormValues {
  endpoint: string;
  primaryLocale: string;
  secondaryLocale: string;
  currency: string;
  replaceCredentials: boolean;
  credentials: Record<string, string>;
}
