import { httpClient } from "@/app/providers/http";

import type {
  CreateMessageTemplatePayload,
  CreateProviderConnectionPayload,
  CreateTemplateVersionPayload,
  ListMessageTemplatesResponse,
  ListOutboundMessagesParams,
  ListOutboundMessagesResponse,
  ListProviderConnectionsResponse,
  MessageTemplate,
  ProviderConnection,
  ProviderConnector,
  ProviderConnectorCatalog,
  SendCommunicationPayload,
  SendCommunicationResponse,
  TemplateVersion,
  UpdateProviderConnectionStatusPayload,
  UpdateProviderConnectorStatusPayload,
} from "./types";

export const communicationApi = {
  importProviderConnectorYaml: async (yamlContent: string) =>
    (
      await httpClient.post<ProviderConnector>(
        "/communication/providers/connectors/import-yaml",
        {
          yaml_content: yamlContent,
        },
      )
    ).data,
  listProviderCatalog: async () =>
    (
      await httpClient.get<ProviderConnectorCatalog>(
        "/communication/providers/connectors",
      )
    ).data,
  updateProviderConnectorStatus: async ({
    provider_connector_id,
    status,
  }: UpdateProviderConnectorStatusPayload) =>
    (
      await httpClient.patch<ProviderConnector>(
        `/communication/providers/connectors/${provider_connector_id}/status`,
        { status },
      )
    ).data,
  deleteProviderConnector: async (providerConnectorId: string) => {
    await httpClient.delete(
      `/communication/providers/connectors/${providerConnectorId}`,
    );
  },
  createProviderConnection: async (payload: CreateProviderConnectionPayload) =>
    (
      await httpClient.post<ProviderConnection>(
        "/communication/providers/connections",
        payload,
      )
    ).data,
  listProviderConnections: async () =>
    (
      await httpClient.get<ListProviderConnectionsResponse>(
        "/communication/providers/connections",
      )
    ).data,
  updateProviderConnectionStatus: async ({
    provider_connection_id,
    status,
  }: UpdateProviderConnectionStatusPayload) =>
    (
      await httpClient.patch<ProviderConnection>(
        `/communication/providers/connections/${provider_connection_id}/status`,
        { status },
      )
    ).data,
  deleteProviderConnection: async (providerConnectionId: string) => {
    await httpClient.delete(
      `/communication/providers/connections/${providerConnectionId}`,
    );
  },
  createMessageTemplate: async (payload: CreateMessageTemplatePayload) =>
    (
      await httpClient.post<MessageTemplate>(
        "/communication/templates",
        payload,
      )
    ).data,
  createTemplateVersion: async (
    templateId: string,
    payload: CreateTemplateVersionPayload,
  ) =>
    (
      await httpClient.post<TemplateVersion>(
        `/communication/templates/${templateId}/versions`,
        payload,
      )
    ).data,
  activateTemplateVersion: async (templateId: string, versionId: string) =>
    (
      await httpClient.post<TemplateVersion>(
        `/communication/templates/${templateId}/versions/${versionId}/activate`,
      )
    ).data,
  listMessageTemplates: async () =>
    (
      await httpClient.get<ListMessageTemplatesResponse>(
        "/communication/templates",
      )
    ).data,
  sendCommunication: async (payload: SendCommunicationPayload) =>
    (
      await httpClient.post<SendCommunicationResponse>(
        "/communication/send",
        payload,
      )
    ).data,
  listOutboundMessages: async (params: ListOutboundMessagesParams) =>
    (
      await httpClient.get<ListOutboundMessagesResponse>(
        "/communication/messages",
        { params },
      )
    ).data,
};
