import { computed, watch, type ComputedRef, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { PublicationFilters } from "./publication.types";
import type { Channel } from "./channel.types";
import {
  parsePublicationFilters,
  publicationPaginationQuery,
} from "./publication.filters";
interface PublicationsPageState {
  filters: ComputedRef<PublicationFilters>;
  setSearch(value: string): void;
  setLocale(value: string): void;
  setPagination(value: { page: number; limit: number }): void;
}
export function usePublicationsPageState(
  channel: Ref<Channel | undefined>,
): PublicationsPageState {
  const route = useRoute(),
    router = useRouter();
  const filters = computed<PublicationFilters>(() =>
    parsePublicationFilters(route.query),
  );
  function setSearch(value: string): void {
    void router.replace({
      query: { ...route.query, q: value || undefined, offset: undefined },
    });
  }
  function setLocale(value: string): void {
    void router.replace({
      query: { ...route.query, locale: value || undefined, offset: undefined },
    });
  }
  function setPagination(value: { page: number; limit: number }): void {
    void router.replace({
      query: { ...route.query, ...publicationPaginationQuery(value) },
    });
  }
  watch(
    [() => channel.value?.config.settings, () => filters.value.locale],
    ([settings, requested]) => {
      if (!settings || !requested) return;
      const locales = Array.isArray(settings.locales)
        ? settings.locales
        : [settings.locale];
      if (!locales.includes(requested)) setLocale("");
    },
    { immediate: true },
  );
  return { filters, setSearch, setLocale, setPagination };
}
