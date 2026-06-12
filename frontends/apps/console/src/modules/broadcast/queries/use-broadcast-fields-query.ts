import { useQuery } from "@tanstack/vue-query";

import { broadcastApi } from "@/modules/broadcast/api";
import { broadcastQueryKeys } from "@/modules/broadcast/model/broadcast.query-keys";

export function useBroadcastFieldsQuery() {
  return useQuery({
    queryKey: broadcastQueryKeys.fields(),
    queryFn: broadcastApi.describeFields,
    retry: false,
  });
}
