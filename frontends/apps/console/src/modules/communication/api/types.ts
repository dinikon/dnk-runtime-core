export type JsonPrimitive = string | number | boolean | null;

export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface CommunicationJsonSchema {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: JsonValue;
  format?: string;
  maxLength?: number;
  enum?: JsonPrimitive[];
  properties?: Record<string, CommunicationJsonSchema>;
  required?: string[];
}

export type JsonObject = Record<string, JsonValue>;

export type ProviderConnectorStatus = "ACTIVE" | "DISABLED" | "ARCHIVED";

export type ProviderConnectorMutableStatus = "ACTIVE" | "DISABLED";

export type ProviderConnectionStatus = "ACTIVE" | "DISABLED" | "ARCHIVED";

export type ProviderConnectionMutableStatus = "ACTIVE" | "DISABLED";

export interface ProviderConnector {
  provider_connector_id: string;
  provider_code: string;
  provider_name: string;
  version: string;
  connector_type: string;
  channels: string[];
  config_schema: CommunicationJsonSchema;
  secrets_schema: CommunicationJsonSchema;
  status: ProviderConnectorStatus;
  created_at: string;
  updated_at: string;
}

export interface ProviderMessageType {
  provider_message_type_id: string;
  provider_connector_id: string;
  message_type_code: string;
  channel_code: string;
  name: string;
  field_schema: CommunicationJsonSchema;
  ui_schema: Record<string, JsonValue>;
  is_active: boolean;
}

export interface ProviderConnectorCatalog {
  connectors: ProviderConnector[];
  message_types: ProviderMessageType[];
}

export interface UpdateProviderConnectorStatusPayload {
  provider_connector_id: string;
  status: ProviderConnectorMutableStatus;
}

export interface ProviderConnection {
  provider_connection_id: string;
  tenant_id: string;
  provider_connector_id: string;
  connection_name: string;
  channel_code: string;
  config: JsonObject;
  secret_ref: string | null;
  has_secrets: boolean;
  status: ProviderConnectionStatus;
  created_at: string;
  updated_at: string;
}

export interface ListProviderConnectionsResponse {
  items: ProviderConnection[];
}

export interface CreateProviderConnectionPayload {
  provider_connector_id: string;
  connection_name: string;
  channel_code: string;
  config: JsonObject;
  secrets: JsonObject;
  secret_ref: string | null;
}

export interface UpdateProviderConnectionStatusPayload {
  provider_connection_id: string;
  status: ProviderConnectionMutableStatus;
}

export interface MessageTemplate {
  template_id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  provider_connector_id: string;
  provider_message_type_id: string;
  channel_code: string;
  status: string;
  created_at: string;
  updated_at: string;
  active_version_id: string | null;
  active_version: string | null;
}

export interface ListMessageTemplatesResponse {
  items: MessageTemplate[];
}

export interface CreateMessageTemplatePayload {
  name: string;
  description: string | null;
  provider_connector_id: string;
  provider_message_type_id: string;
  channel_code: string;
}

export interface TemplateVersion {
  template_version_id: string;
  template_id: string;
  version: string;
  template_payload: JsonObject;
  variables_schema: JsonObject;
  status: string;
  created_at: string;
  activated_at: string | null;
}

export interface CreateTemplateVersionPayload {
  template_payload: JsonObject;
  variables_schema: JsonObject;
}

export interface SendCommunicationPayload {
  initiator_type: string;
  initiator_ref_id: string;
  correlation_id: string;
  idempotency_key: string;
  channel_code: string;
  template_id: string;
  recipient_identifier_type: string;
  recipient_address: string;
  recipient_snapshot: JsonObject;
  variables: JsonObject;
  scheduled_at: string | null;
  priority: number;
}

export interface SendCommunicationResponse {
  communication_request_id: string;
  outbound_message_id: string;
  status: string;
  internal_status: string;
  idempotent: boolean;
}

export interface OutboundMessage {
  outbound_message_id: string;
  tenant_id: string;
  communication_request_id: string;
  provider_connection_id: string;
  channel_code: string;
  recipient_identifier_type: string;
  recipient_address: string;
  recipient_snapshot: JsonObject;
  rendered_payload: JsonObject;
  provider_request_payload: JsonObject;
  external_message_id: string | null;
  external_status: string | null;
  internal_status: string;
  error_code: string | null;
  error_message: string | null;
  queued_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListOutboundMessagesResponse {
  items: OutboundMessage[];
}

export interface ListOutboundMessagesParams {
  limit: number;
  offset: number;
}
