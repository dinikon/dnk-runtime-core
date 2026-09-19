<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import type { OfferFilters, PartnerOffer } from "../model/types";
import { priceListKeys } from "../model/query-keys";
import { usePriceListsQuery } from "../model/use-price-lists-query";
import { usePurchaseOffersQuery } from "../model/use-purchase-offers-query";
import {
  defaultOfferFilters,
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

const lists = usePriceListsQuery();
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
  queryKey: computed(() => priceListKeys.history(selectedOffer.value?.id ?? "")),
  queryFn: () => priceListsApi.history(selectedOffer.value!.id),
  enabled: computed(() => selectedOffer.value !== null),
});
const totalPages = computed(() =>
  Math.max(1, Math.ceil((offers.data.value?.total ?? 0) / filters.value.limit)),
);
const hasFilters = computed(() =>
  Object.entries(filters.value).some(([key, value]) =>
    !["sort", "direction", "page", "limit"].includes(key) && value !== "",
  ),
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <PurchaseOffersHeader />
    <PurchaseOffersFilters :filters="filters" :price-lists="lists.data.value ?? []" :has-filters="hasFilters" :range-error="rangeError" @set-filter="setFilter" @reset="resetFilters" />
    <PurchaseOffersTable :items="offers.data.value?.items ?? []" :filters="filters" :pending="offers.isPending.value" :failed="offers.isError.value" :filtered="hasFilters" @sort="sortBy" @retry="offers.refetch()" @select="selectedOffer = $event" />
    <PurchaseOffersFooter :total="offers.data.value?.total ?? 0" :page="filters.page" :total-pages="totalPages" @page="goToPage" />
    <OfferHistoryDrawer :offer="selectedOffer" :items="history.data.value?.items ?? []" :pending="history.isPending.value" @close="selectedOffer = null" />
  </div>
</template>
