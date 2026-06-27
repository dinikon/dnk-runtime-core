<script setup lang="ts">
import { Search } from "lucide-vue-next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useRouteQueryPatch,
  useRouteSearchQuery,
} from "@/modules/communication/composables/use-route-query";

const props = defineProps<{
  actionLabel: string;
  actionQueryKey: string;
  actionQueryValue: string;
  searchPlaceholder: string;
}>();

const searchQuery = useRouteSearchQuery();
const { patchQuery } = useRouteQueryPatch();

function updateSearch(value: string | number) {
  patchQuery({ q: String(value).trim() || undefined });
}

function openActionSheet() {
  patchQuery({ [props.actionQueryKey]: props.actionQueryValue });
}
</script>

<template>
  <div class="grid shrink-0 gap-3 rounded-lg border p-3">
    <div class="grid gap-3 md:grid-cols-[minmax(16rem,1fr)_auto]">
      <div class="relative">
        <Search
          class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          :model-value="searchQuery"
          class="pl-9"
          :placeholder="searchPlaceholder"
          type="search"
          @update:model-value="updateSearch"
        />
      </div>

      <Button type="button" @click="openActionSheet">
        <slot name="action-icon" />
        {{ actionLabel }}
      </Button>
    </div>
  </div>
</template>
