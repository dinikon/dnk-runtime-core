<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import type { OfferFilters, OfferHistoryFilters, PartnerOffer, PriceListScope } from "../model/types";
import { priceListKeys } from "../model/query-keys";
import { usePriceListsQuery } from "../model/use-price-lists-query";
import { usePurchaseOffersQuery } from "../model/use-purchase-offers-query";
import {
  defaultOfferFilters,
  defaultOfferHistoryFilters,
  filtersFromQuery,
  filtersToQuery,
} from "../model/query-state";
import OfferHistoryDrawer from "../ui/offers/OfferHistoryDrawer.vue";
import PurchaseOffersFilters from "../ui/offers/PurchaseOffersFilters.vue";
import PurchaseOffersFooter from "../ui/offers/PurchaseOffersFooter.vue";
import PurchaseOffersHeader from "../ui/offers/PurchaseOffersHeader.vue";
import PurchaseOffersTable from "../ui/offers/PurchaseOffersTable.vue";

const route = useRoute();
const router = useRouter();
const filters = ref(filtersFromQuery(route.query));
const historyFilters = ref<OfferHistoryFilters>({ ...defaultOfferHistoryFilters });
const selectedOffer = ref<PartnerOffer | null>(null);
let searchTimer: ReturnType<typeof setTimeout> | undefined;

watch(
  () => route.query,
  (query) => { filters.value = filtersFromQuery(query); },
);
function applyFilters(immediate = true) {
  filters.value.page = 1;
  if (searchTimer) clearTimeout(searchTimer);
  const update = () => router.replace({ query: filtersToQuery(filters.value) });
  if (immediate) update(); else searchTimer = setTimeout(update, 350);
}
function resetFilters() {
  filters.value = { ...defaultOfferFilters };
  void router.replace({ query: filtersToQuery(filters.value) });
}
function setFilter(key: keyof OfferFilters, value: string, immediate: boolean) {
  if (key === "page" || key === "limit") return;
  Object.assign(filters.value, { [key]: value });
  applyFilters(immediate);
}
function sortBy(field: string) {
  if (filters.value.sort === field) {
    filters.value.direction = filters.value.direction === "desc" ? "asc" : "desc";
  } else {
    filters.value.sort = field;
    filters.value.direction = "desc";
  }
  applyFilters();
}
function goToPage(page: number) {
  filters.value.page = page;
  void router.replace({ query: filtersToQuery(filters.value) });
}

const priceListScope = computed<PriceListScope>(() => filters.value.includeArchived ? "all" : "current");
const lists = usePriceListsQuery(priceListScope);
const rangeError = computed(() => {
  const ranges = [
    [filters.value.purchasePriceMin, filters.value.purchasePriceMax],
    [filters.value.incomeMin, filters.value.incomeMax],
    [filters.value.marginMin, filters.value.marginMax],
  ];
  return ranges.some(([minimum, maximum]) =>
    minimum !== "" && maximum !== "" && Number(minimum) > Number(maximum),
  );
});
const offers = usePurchaseOffersQuery(filters, computed(() => !rangeError.value));
const history = useQuery({
  queryKey: computed(() => priceListKeys.history(selectedOffer.value?.id ?? "", { ...historyFilters.value })),
  queryFn: ({ signal }) => priceListsApi.history(selectedOffer.value!.id, historyFilters.value, signal),
  enabled: computed(() => selectedOffer.value !== null),
});
const totalPages = computed(() =>
  Math.max(1, Math.ceil((offers.data.value?.total ?? 0) / filters.value.limit)),
);
const hasFilters = computed(() =>
  Object.entries(filters.value).some(([key, value]) =>
    !["sort", "direction", "page", "limit"].includes(key) && (typeof value === "boolean" ? value : value !== ""),
  ),
);
function selectOffer(offer: PartnerOffer) {
  selectedOffer.value = offer;
  historyFilters.value = { ...defaultOfferHistoryFilters };
}
function closeHistory() {
  selectedOffer.value = null;
  historyFilters.value = { ...defaultOfferHistoryFilters };
}
function setHistoryFilter(key: keyof OfferHistoryFilters, value: string) {
  Object.assign(historyFilters.value, { [key]: value, page: 1 });
}
function sortHistory(field: string) {
  historyFilters.value = {
    ...historyFilters.value,
    sort: field,
    direction: historyFilters.value.sort === field && historyFilters.value.direction === "desc" ? "asc" : "desc",
    page: 1,
  };
}
function goToHistoryPage(page: number) {
  historyFilters.value = { ...historyFilters.value, page };
}
function resetHistoryFilters() {
  historyFilters.value = { ...defaultOfferHistoryFilters };
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <PurchaseOffersHeader />
    <PurchaseOffersFilters :filters="filters" :price-lists="lists.data.value ?? []" :has-filters="hasFilters" :range-error="rangeError" @set-filter="setFilter" @reset="resetFilters" />
    <PurchaseOffersTable :items="offers.data.value?.items ?? []" :filters="filters" :pending="offers.isPending.value" :failed="offers.isError.value" :filtered="hasFilters" @sort="sortBy" @retry="offers.refetch()" @select="selectOffer" />
    <PurchaseOffersFooter :total="offers.data.value?.total ?? 0" :page="filters.page" :total-pages="totalPages" @page="goToPage" />
    <OfferHistoryDrawer :offer="selectedOffer" :items="history.data.value?.items ?? []" :filters="historyFilters" :total="history.data.value?.total ?? 0" :pending="history.isPending.value" :failed="history.isError.value" @close="closeHistory" @set-filter="setHistoryFilter" @sort="sortHistory" @page="goToHistoryPage" @reset="resetHistoryFilters" @retry="history.refetch()" />
  </div>
</template>
