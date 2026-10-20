import {
  computed,
  ref,
  toValue,
  type MaybeRefOrGetter,
  type ComputedRef,
  type Ref,
} from "vue";
import type { CatalogCandidatesInput } from "./catalog-links.types";
interface CatalogCandidateState {
  locale: Ref<string>;
  page: Ref<number>;
  filters: ComputedRef<CatalogCandidatesInput>;
  reset: (value: string) => void;
  setSearch: (value: string) => void;
  setPage: (value: number) => void;
  setLocale: (value: string) => void;
}
export function useCatalogCandidateState(
  publicationId: MaybeRefOrGetter<string>,
): CatalogCandidateState {
  const search = ref(""),
    locale = ref(""),
    page = ref(1);
  const filters = computed(() => ({
    publicationId: toValue(publicationId),
    locale: locale.value,
    search: search.value,
    offset: (page.value - 1) * 20,
    limit: 20,
  }));
  function reset(value: string): void {
    search.value = "";
    locale.value = value;
    page.value = 1;
  }
  function setSearch(value: string): void {
    search.value = value;
    page.value = 1;
  }
  function setPage(value: number): void {
    page.value = value;
  }
  function setLocale(value: string): void {
    locale.value = value;
    page.value = 1;
  }
  return { locale, page, filters, reset, setSearch, setPage, setLocale };
}
