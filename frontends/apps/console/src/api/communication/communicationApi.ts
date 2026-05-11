import {httpClient} from "@/api/http/httpClient";
import type {
    CreateMessageTemplatePayload,
    CreateProviderConnectionPayload,
    CreateTemplateVersionPayload,
    ListMessageTemplatesResponse,
    ListOutboundMessagesResponse,
    ListProviderConnectionsResponse,
    ListProviderConnectorsResponse,
    MessageTemplate,
    ProviderConnection,
    ProviderConnector,
    SendCommunicationPayload,
    SendCommunicationResponse,
    TemplateVersion
} from "@/api/communication/types";

export const communicationApi = {
    importConnectorYaml: async (yamlContent: string): Promise<ProviderConnector> =>
        (await httpClient.post<ProviderConnector>("/communication/providers/connectors/import-yaml", {
            yaml_content: yamlContent
        })).data,

    listProviderConnectors: async (): Promise<ListProviderConnectorsResponse> =>
        (await httpClient.get<ListProviderConnectorsResponse>("/communication/providers/connectors")).data,

    createProviderConnection: async (payload: CreateProviderConnectionPayload): Promise<ProviderConnection> =>
        (await httpClient.post<ProviderConnection>("/communication/providers/connections", payload)).data,

    listProviderConnections: async (): Promise<ListProviderConnectionsResponse> =>
        (await httpClient.get<ListProviderConnectionsResponse>("/communication/providers/connections")).data,

    createTemplate: async (payload: CreateMessageTemplatePayload): Promise<MessageTemplate> =>
        (await httpClient.post<MessageTemplate>("/communication/templates", payload)).data,

    createTemplateVersion: async (templateId: string, payload: CreateTemplateVersionPayload): Promise<TemplateVersion> =>
        (await httpClient.post<TemplateVersion>(`/communication/templates/${templateId}/versions`, payload)).data,

    activateTemplateVersion: async (templateId: string, versionId: string): Promise<TemplateVersion> =>
        (await httpClient.post<TemplateVersion>(`/communication/templates/${templateId}/versions/${versionId}/activate`)).data,

    listTemplates: async (): Promise<ListMessageTemplatesResponse> =>
        (await httpClient.get<ListMessageTemplatesResponse>("/communication/templates")).data,

    sendCommunication: async (payload: SendCommunicationPayload): Promise<SendCommunicationResponse> =>
        (await httpClient.post<SendCommunicationResponse>("/communication/send", payload)).data,

    listMessages: async (): Promise<ListOutboundMessagesResponse> =>
        (await httpClient.get<ListOutboundMessagesResponse>("/communication/messages")).data
};

