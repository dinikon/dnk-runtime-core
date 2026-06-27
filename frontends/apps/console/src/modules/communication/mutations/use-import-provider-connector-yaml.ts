import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useImportProviderConnectorYamlMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: communicationApi.importProviderConnectorYaml,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.providerCatalog(),
      });
    },
  });
}
