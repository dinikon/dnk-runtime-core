export type ChannelType = "cms" | "marketplace" | "shop";
export type ChannelStatus = "unverified" | "connected" | "error";
export interface Platform {
  kind: string;
  type: ChannelType;
  label: string;
  can_configure: boolean;
  unavailable_reason: string | null;
}
export interface PropertySchema {
  type: "string";
  title: string;
  minLength?: number;
  maxLength?: number;
  format?: string;
  writeOnly?: boolean;
}
export interface ConnectionSchema {
  json_schema: {
    $schema: string;
    type: "object";
    properties: Record<string, PropertySchema>;
    required: string[];
    additionalProperties: false;
  };
  ui_schema: {
    property: string;
    widget: "text" | "url" | "password";
    help_text: string;
  }[];
}
export interface PlatformConfig extends Platform {
  config_version: number;
  config: {
    connection: ConnectionSchema | null;
    capabilities: Record<string, boolean>;
  };
}
export interface Channel {
  id: string;
  name: string;
  kind: string;
  type: ChannelType;
  config_version: number;
  connection_settings: Record<string, string>;
  configured_secret_fields: string[];
  is_active: boolean;
  status: ChannelStatus;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}
export interface CreateChannel {
  name: string;
  kind: string;
  config_version: number;
  connection_settings: Record<string, string>;
  is_active: boolean;
}
export interface UpdateChannel {
  name?: string;
  is_active?: boolean;
  config_version?: number;
  connection_settings?: Record<string, string>;
}
export const typeLabels: Record<ChannelType, string> = {
  marketplace: "Маркетплейсы",
  cms: "CMS",
  shop: "Интернет-магазины",
};
export const statusLabels: Record<ChannelStatus, string> = {
  unverified: "Не проверен",
  connected: "Подключён",
  error: "Ошибка подключения",
};
