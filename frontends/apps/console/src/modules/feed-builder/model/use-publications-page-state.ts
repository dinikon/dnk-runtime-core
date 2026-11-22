import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import type {
  PublicationFilters,
  PublicationStatus,
} from "./feed-publication.types";
export function usePublicationsPageState(): {
  filters: ComputedRef<PublicationFilters>;
  setSearch(value: string): void;
  setStatus(value: string): void;
  setLocale(value: string): void;
  setOffset(value: number): void;
} {
  const route = useRoute(),
    router = useRouter();
  const filters = computed<PublicationFilters>(() => ({
    search:
      typeof route.query.search === "string"
        ? route.query.search.slice(0, 255)
        : "",
    status: ["DRAFT", "ENABLED", "PAUSED", "ARCHIVED"].includes(
      String(route.query.status),
    )
      ? (route.query.status as PublicationStatus)
      : "",
    locale:
      typeof route.query.locale === "string" &&
      /^[A-Za-z0-9-]{2,64}$/.test(route.query.locale)
        ? route.query.locale
        : "uk",
    offset: /^\d+$/.test(String(route.query.offset))
      ? Math.min(Number(route.query.offset), 10000000)
      : 0,
    limit: 25,
  }));
  function set(values: Record<string, string | number | undefined>): void {
    void router.replace({ query: { ...route.query, ...values } });
  }
  return {
    filters,
    setSearch: (search: string): void =>
      set({ search: search || undefined, offset: undefined }),
    setStatus: (status: string): void =>
      set({ status: status || undefined, offset: undefined }),
    setLocale: (locale: string): void => set({ locale, offset: undefined }),
    setOffset: (offset: number): void => set({ offset: offset || undefined }),
  };
}
