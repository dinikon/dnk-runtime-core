import {useMutation, useQuery, useQueryClient} from "@tanstack/vue-query";

import {
  communicationApi,
  type CreateProviderConnectionPayload,
} from "@/api/communication";

export const communicationProviderQueryKeys = {
  all: ["communication", "providers"] as const,
  connectors: () => [...communicationProviderQueryKeys.all, "connectors"] as const,
  connections: () => [...communicationProviderQueryKeys.all, "connections"] as const,
};

export function useProviderConnectorsQuery() {
  return useQuery({
    queryKey: communicationProviderQueryKeys.connectors(),
    queryFn: () => communicationApi.listProviderConnectors(),
  });
}

export function useProviderConnectionsQuery() {
  return useQuery({
    queryKey: communicationProviderQueryKeys.connections(),
    queryFn: () => communicationApi.listProviderConnections(),
  });
}

export function useImportProviderConnectorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (yamlContent: string) => communicationApi.importConnectorYaml(yamlContent),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: communicationProviderQueryKeys.connectors(),
      });
    },
  });
}

export function useCreateProviderConnectionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateProviderConnectionPayload) => communicationApi.createProviderConnection(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: communicationProviderQueryKeys.connections(),
      });
    },
  });
}
