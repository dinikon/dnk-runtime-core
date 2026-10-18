import { computed } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { ConnectionReferences } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useConnectionReferencesQuery(
  ctx: ChannelsContext,
): UseQueryReturnType<ConnectionReferences, ChannelsApiError> {
  return useQuery<ConnectionReferences, ChannelsApiError>({
    queryKey: computed(() => channelsKeys.references(ctx.scope.value)),
    queryFn: ({ signal }) => channelsApi.references(signal),
    enabled: ctx.enabled,
    retry: false,
    refetchIntervalInBackground: false,
  });
}
