<script setup lang="ts">
import { ref, watch } from "vue";
import { Plus, Search } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const route = useRoute();
const router = useRouter();
const search = ref(searchFromRoute());

watch(
  () => route.query.q,
  () => {
    search.value = searchFromRoute();
  },
);

function searchFromRoute(): string {
  const value = route.query.q;
  return typeof value === "string" ? value : "";
}

function updateSearch(value: string | number) {
  search.value = String(value);
  patchQuery({ q: search.value.trim() || undefined });
}

function openImportSheet() {
  patchQuery({ import: "provider" });
}

function patchQuery(patch: Record<string, string | undefined>) {
  const nextQuery = { ...route.query };

  for (const [key, value] of Object.entries(patch)) {
    if (!value) {
      delete nextQuery[key];
    } else {
      nextQuery[key] = value;
    }
  }

  router.replace({ query: nextQuery });
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
          :model-value="search"
          class="pl-9"
          placeholder="Search providers"
          type="search"
          @update:model-value="updateSearch"
        />
      </div>

      <Button type="button" @click="openImportSheet">
        <Plus class="size-4" />
        Add
      </Button>
    </div>
  </div>
</template>
