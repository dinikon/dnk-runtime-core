import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { ChannelFilters } from "./channel.types";
interface ChannelsPageState {
  filters: ComputedRef<ChannelFilters>;
  setFilter(key: "q" | "platform" | "status", value: string): void;
  setOffset(offset: number): void;
}
export function useChannelsPageState(): ChannelsPageState {
  const route = useRoute(),
    router = useRouter();
  const filters = computed<ChannelFilters>(() => ({
    search: String(route.query.q ?? ""),
    platformKind: String(route.query.platform ?? ""),
    status: ["pending", "verified", "error"].includes(
      String(route.query.status),
    )
      ? String(route.query.status)
      : "",
    offset: Math.min(
      2147483600,
      Math.max(0, Math.floor(Number(route.query.offset) || 0)),
    ),
  }));
  function setFilter(key: "q" | "platform" | "status", value: string): void {
    void router.replace({
      query: { ...route.query, [key]: value || undefined, offset: undefined },
      hash: route.hash,
    });
  }
  function setOffset(offset: number): void {
    void router.replace({
      query: { ...route.query, offset: Math.max(0, offset) || undefined },
      hash: route.hash,
    });
  }
  return { filters, setFilter, setOffset };
}
