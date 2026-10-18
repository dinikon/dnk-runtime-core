import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { contactPointsApi } from "../api/contact-points.api";
export const contactPointKeys = {
  labels: ["contact-points", "labels"] as const,
};
export function useContactPointLabels(
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  return useQuery({
    queryKey: contactPointKeys.labels,
    queryFn: ({ signal }) => contactPointsApi.labels(signal),
    enabled: computed(() => toValue(enabled)),
  });
}
