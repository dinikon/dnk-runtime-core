import { useQuery } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useMessageTemplatesQuery() {
  return useQuery({
    queryKey: communicationQueryKeys.messageTemplates(),
    queryFn: communicationApi.listMessageTemplates,
    retry: false,
  });
}
