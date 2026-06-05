import { useQuery } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useProviderCatalogQuery() {
  return useQuery({
    queryKey: communicationQueryKeys.providerCatalog(),
    queryFn: communicationApi.listProviderCatalog,
    retry: false,
  });
}
