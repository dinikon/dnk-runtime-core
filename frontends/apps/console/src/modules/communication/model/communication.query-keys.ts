export const communicationQueryKeys = {
  all: ["communication"] as const,
  providerCatalog: () =>
    [...communicationQueryKeys.all, "provider-catalog"] as const,
  providerConnections: () =>
    [...communicationQueryKeys.all, "provider-connections"] as const,
  messageTemplates: () =>
    [...communicationQueryKeys.all, "message-templates"] as const,
  outboundMessages: () =>
    [...communicationQueryKeys.all, "outbound-messages"] as const,
  outboundMessagesPage: (params: { limit: number; offset: number }) =>
    [...communicationQueryKeys.outboundMessages(), params] as const,
};
