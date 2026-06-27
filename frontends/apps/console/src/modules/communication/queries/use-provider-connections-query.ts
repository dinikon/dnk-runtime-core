import { useQuery } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useProviderConnectionsQuery() {
  return useQuery({
    queryKey: communicationQueryKeys.providerConnections(),
    queryFn: communicationApi.listProviderConnections,
    retry: false,
  });
}
