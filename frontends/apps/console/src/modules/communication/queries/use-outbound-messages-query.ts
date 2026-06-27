import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type { ListOutboundMessagesParams } from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

export function useOutboundMessagesQuery(
  params: MaybeRefOrGetter<ListOutboundMessagesParams>,
) {
  return useQuery({
    queryKey: computed(() =>
      communicationQueryKeys.outboundMessagesPage(toValue(params)),
    ),
    queryFn: () => communicationApi.listOutboundMessages(toValue(params)),
    retry: false,
  });
}
