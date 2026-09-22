import { computed, ref, watch } from "vue";
import { refDebounced } from "@vueuse/core";
import { useRoute, useRouter } from "vue-router";

const PAGE_SIZE = 25;

function queryValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function useCrmListState() {
  const route = useRoute();
  const router = useRouter();
  const search = ref(queryValue(route.query.q));
  const debouncedSearch = refDebounced(search, 300);
  const page = computed(() => {
    const value = Number.parseInt(queryValue(route.query.page), 10);
    return Number.isFinite(value) && value > 0 ? value : 1;
  });
  const params = computed(() => ({
    q: debouncedSearch.value.trim(),
    limit: PAGE_SIZE,
    offset: (page.value - 1) * PAGE_SIZE,
  }));

  watch(debouncedSearch, async (value) => {
    const q = value.trim();
    if (q === queryValue(route.query.q)) return;
    await router.replace({
      query: q ? { q } : {},
    });
  });

  watch(
    () => route.query.q,
    (value) => {
      const next = queryValue(value);
      if (next !== debouncedSearch.value) search.value = next;
    },
  );

  async function setPage(value: number) {
    const q = debouncedSearch.value.trim();
    await router.replace({
      query: {
        ...(q ? { q } : {}),
        ...(value > 1 ? { page: String(value) } : {}),
      },
    });
  }

  return { page, params, search, setPage, pageSize: PAGE_SIZE };
}
