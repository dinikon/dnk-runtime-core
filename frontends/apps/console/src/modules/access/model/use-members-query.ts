import { useQuery } from "@tanstack/vue-query";

import { accessApi } from "../api/access.api";
import { accessQueryKeys } from "./access.query-keys";

export function useMembersQuery() {
  return useQuery({
    queryKey: accessQueryKeys.members(),
    queryFn: accessApi.members,
    retry: false,
  });
}
