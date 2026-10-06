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

export interface PublicationListItem {
  id: string;
  external_id: string;
  title: string | null;
  sku: string | null;
  thumbnail_url: string | null;
  price: string | null;
  currency: string | null;
  availability: string | null;
  source_status: string | null;
  variations_count: number;
  observed_at: string;
}
export interface PublicationPage {
  items: PublicationListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface PublicationAttribute {
  name: string;
  value: string;
  unit: string | null;
}
export interface PublicationVariant {
  id: string;
  external_id: string;
  title: string | null;
  sku: string | null;
  price: string | null;
  currency: string | null;
  quantity: string | null;
  availability: string | null;
  source_status: string | null;
  attributes: PublicationAttribute[];
}
export interface PublicationDetails {
  id: string;
  channel_id: string;
  external_id: string;
  resource_type: string;
  title: string | null;
  sku: string | null;
  external_url: string | null;
  description_html: string | null;
  short_description_html: string | null;
  price: string | null;
  regular_price: string | null;
  sale_price: string | null;
  currency: string | null;
  quantity: string | null;
  availability: string | null;
  source_status: string | null;
  product_type: string | null;
  images: { url: string; alt: string }[];
  categories: { external_id: string; name: string }[];
  attributes: PublicationAttribute[];
  variants: PublicationVariant[];
  expected_variations: number | null;
  warnings: string[];
  schema_version: number;
  revision: number;
  observed_at: string;
}
export interface PublicationImportRun {
  id: string;
  channel_id: string;
  status: "queued" | "running" | "succeeded" | "partial" | "failed";
  pages: number;
  resources: number;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}
