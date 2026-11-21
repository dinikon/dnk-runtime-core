import type { JsonObject } from "../model/channel.types";
export interface ChannelDto {
  id: string;
  name: string;
  platform_kind: string;
  revision: number;
  config: {
    version: number;
    endpoint: string;
    settings: JsonObject;
  };
  config_revision: number;
  identity: { namespace: string; key: string } | null;
  verification: {
    job_id: string;
    config_revision: number;
    status: "pending" | "verified" | "error";
    checked_at: string | null;
    error_code: string | null;
  };
  recovery_required: boolean;
  available_capabilities: string[];
  created_at: string;
  updated_at: string;
}
export interface ChannelPageDto {
  items: ChannelDto[];
  total: number;
  offset: number;
  limit: number;
}
export interface PlatformDto {
  kind: string;
  title: string;
  config_version: number;
  config_schema: JsonObject;
  credentials_schema: JsonObject;
  supported_capabilities: string[];
}
export interface CreateChannelDto {
  name: string;
  platform_kind: string;
  config: ChannelDto["config"];
  credentials: JsonObject;
}
export interface UpdateChannelDto {
  expected_revision: number;
  name: string;
  config: ChannelDto["config"];
  credentials?: JsonObject;
}
export interface SavedChannelDto {
  id: string;
  revision: number;
  verification_job_id: string;
}
