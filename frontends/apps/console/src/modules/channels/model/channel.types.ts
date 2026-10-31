export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };
export interface ChannelConfig {
  version: number;
  endpoint: string;
  settings: JsonObject;
}
export interface Verification {
  jobId: string;
  configRevision: number;
  status: "pending" | "verified" | "error";
  checkedAt: string | null;
  errorCode: string | null;
}
export interface Channel {
  id: string;
  name: string;
  platformKind: string;
  revision: number;
  config: ChannelConfig;
  configRevision: number;
  identity: { namespace: string; key: string } | null;
  verification: Verification;
  recoveryRequired: boolean;
  availableCapabilities: string[];
  createdAt: string;
  updatedAt: string;
}
export interface ChannelPage {
  items: Channel[];
  total: number;
  offset: number;
  limit: number;
}
export interface Platform {
  kind: string;
  title: string;
  configVersion: number;
  configSchema: JsonObject;
  credentialsSchema: JsonObject;
  supportedCapabilities: string[];
}
export interface ChannelDraft {
  name: string;
  platformKind: string;
  endpoint: string;
  settings: JsonObject;
  credentials: Record<string, string>;
  replaceCredentials: boolean;
}
export interface ChannelSave {
  name: string;
  platformKind: string;
  config: ChannelConfig;
  credentials?: JsonObject;
}
export interface ChannelSaved {
  id: string;
  revision: number;
  verificationJobId: string;
}
export interface ChannelFilters {
  search: string;
  platformKind: string;
  status: string;
  offset: number;
}
export interface SchemaField {
  key: string;
  title: string;
  description?: string;
  required: boolean;
  secret: boolean;
  readOnly: boolean;
  defaultValue: JsonValue;
  options: string[];
  maxLength?: number;
  format?: string;
}
export class ChannelApiError extends Error {
  constructor(
    public code: string,
    public status?: number,
    public field?: string,
  ) {
    super(code);
  }
}
