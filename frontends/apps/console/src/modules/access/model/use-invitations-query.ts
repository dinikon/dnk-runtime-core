import { useQuery } from "@tanstack/vue-query";

import { accessApi } from "../api/access.api";
import { accessQueryKeys } from "./access.query-keys";

export function useInvitationsQuery() {
  return useQuery({
    queryKey: accessQueryKeys.invitations(),
    queryFn: accessApi.invitations,
    retry: false,
  });
}
