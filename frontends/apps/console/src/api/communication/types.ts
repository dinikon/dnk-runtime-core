export interface JsonSchemaProperty {
    type?: string;
    title?: string;
    default?: unknown;
    maxLength?: number;
    format?: string;
}

export interface JsonSchemaObject {
    type?: string;
    required?: string[];
    properties?: Record<string, JsonSchemaProperty>;
}

export interface ProviderConnector {
    provider_connector_id: string;
    provider_code: string;
    provider_name: string;
    version: string;
    connector_type: string;
    channels: string[];
    config_schema: JsonSchemaObject;
    secrets_schema: JsonSchemaObject;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface ProviderMessageType {
    provider_message_type_id: string;
    provider_connector_id: string;
    message_type_code: string;
    channel_code: string;
    name: string;
    field_schema: JsonSchemaObject;
    ui_schema: Record<string, unknown>;
    is_active: boolean;
}

export interface ListProviderConnectorsResponse {
    connectors: ProviderConnector[];
    message_types: ProviderMessageType[];
}

export interface ProviderConnection {
    provider_connection_id: string;
    tenant_id: string;
    provider_connector_id: string;
    connection_code: string;
    connection_name: string;
    channel_code: string;
    config: Record<string, unknown>;
    secret_ref: string | null;
    has_secrets: boolean;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface CreateProviderConnectionPayload {
    provider_connector_id: string;
    connection_code: string;
    connection_name: string;
    channel_code: string;
    config: Record<string, unknown>;
    secrets: Record<string, unknown>;
    secret_ref?: string | null;
}

export interface ListProviderConnectionsResponse {
    items: ProviderConnection[];
}

export interface MessageTemplate {
    template_id: string;
    tenant_id: string;
    template_code: string;
    name: string;
    description: string | null;
    provider_connector_id: string;
    provider_message_type_id: string;
    channel_code: string;
    message_class: string;
    status: string;
    created_at: string;
    updated_at: string;
    active_version_id: string | null;
    active_version_no: number | null;
}

export interface CreateMessageTemplatePayload {
    template_code: string;
    name: string;
    description?: string | null;
    provider_connector_id: string;
    provider_message_type_id: string;
    channel_code: string;
    message_class: string;
}

export interface TemplateVersion {
    template_version_id: string;
    template_id: string;
    version_no: number;
    template_payload: Record<string, unknown>;
    variables_schema: Record<string, unknown>;
    status: string;
    created_at: string;
    activated_at: string | null;
}

export interface CreateTemplateVersionPayload {
    template_payload: Record<string, unknown>;
    variables_schema: Record<string, unknown>;
}

export interface ListMessageTemplatesResponse {
    items: MessageTemplate[];
}

export interface SendCommunicationPayload {
    initiator_type: string;
    message_class: string;
    channel_code: string;
    recipient_address: string;
    template_code?: string | null;
    template_id?: string | null;
    initiator_ref_id?: string | null;
    idempotency_key?: string | null;
    variables: Record<string, unknown>;
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
    contact_id: string | null;
    recipient_address: string;
    rendered_payload: Record<string, unknown>;
    provider_request_payload: Record<string, unknown>;
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

