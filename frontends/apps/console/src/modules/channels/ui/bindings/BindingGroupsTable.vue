<script setup lang="ts">
import { computed } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { Package } from "@lucide/vue";
import { DataTable } from "@/components/custom-ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import PublicationActions from "../PublicationActions.vue";
import {
  bindingPublicationPrice,
  bindingPublicationStock,
} from "../../model/publication-summary";
import {
  bindingModes,
  bindingStates,
  type CatalogBinding,
  type BindingPosition,
} from "../../model/bindings/binding.types";
import { bindingGroupsColumns } from "./binding-groups.columns";

const props = defineProps<{
  items: readonly CatalogBinding[];
  busy: boolean;
  showCatalog: boolean;
}>();
const emit = defineEmits<{
  stock: [group: CatalogBinding];
  edit: [group: CatalogBinding];
  remove: [group: CatalogBinding];
  catalog: [id: string];
  publication: [group: CatalogBinding];
}>();
const mobile = useMediaQuery("(max-width: 639px)");
const columns = computed(() =>
  bindingGroupsColumns
    .filter((column) => props.showCatalog || column.key !== "catalog")
    .map((column) =>
      mobile.value && column.key === "publication"
        ? { ...column, width: 180 }
        : mobile.value && column.key === "actions"
          ? { ...column, pinned: undefined }
          : column,
    ),
);
function publication(group: CatalogBinding): BindingPosition | undefined {
  const id = group.publicationRootId ?? group.items[0]?.publicationId;
  return (
    group.preview.publications.find((position) => position.id === id) ??
    group.preview.publications[0]
  );
}
function canOpen(group: CatalogBinding): boolean {
  return !!(group.publicationRootId ?? group.items[0]?.publicationId);
}
function title(group: CatalogBinding): string {
  return (
    publication(group)?.title ??
    publication(group)?.externalId ??
    "Без названия"
  );
}
</script>

<template>
  <DataTable
    :rows="items"
    :columns="columns"
    :row-key="(group) => group.id"
    caption="Связанные публикации"
    class="max-h-[60dvh] lg:max-h-none"
    @row-activate="!busy && emit('edit', $event)"
  >
    <template #header="{ column }"
      ><span :class="column.key === 'actions' ? 'sr-only' : undefined">{{
        column.label
      }}</span></template
    >
    <template #cell="{ row: group, column }">
      <Button
        v-if="column.key === 'publication'"
        type="button"
        variant="ghost"
        size="sm"
        class="h-auto max-w-full justify-start p-0"
        :disabled="!canOpen(group)"
        :aria-label="`Открыть публикацию ${title(group)}`"
        @click="emit('publication', group)"
      >
        <span
          class="flex size-6 shrink-0 items-center justify-center overflow-hidden rounded bg-muted"
          ><img
            v-if="publication(group)?.imageUrl"
            :src="publication(group)?.imageUrl ?? undefined"
            alt=""
            class="size-full object-cover"
            loading="lazy" /><Package v-else aria-hidden="true"
        /></span>
        <span class="truncate" :title="title(group)">{{ title(group) }}</span>
        <Badge
          v-if="group.preview.publicationCount > 1"
          variant="outline"
          :title="`Публикаций в группе: ${group.preview.publicationCount}`"
          >+{{ group.preview.publicationCount - 1 }}</Badge
        >
      </Button>
      <span
        v-else-if="column.key === 'channel'"
        class="block truncate"
        :title="`${group.channelName} · ${group.platform}`"
        >{{ group.channelName }}</span
      >
      <Button
        v-else-if="column.key === 'catalog'"
        type="button"
        variant="ghost"
        size="sm"
        class="h-auto max-w-full justify-start p-0"
        @click="emit('catalog', group.catalogRootId)"
        ><span
          class="truncate"
          :title="group.preview.catalogRoot?.title ?? group.catalogRootId"
          >{{ group.preview.catalogRoot?.title ?? "Товар недоступен" }}</span
        ></Button
      >
      <span
        v-else-if="column.key === 'mode'"
        class="block truncate"
        :title="bindingModes[group.mode]"
        >{{ bindingModes[group.mode] }}</span
      >
      <span
        v-else-if="column.key === 'price'"
        class="block truncate tabular-nums"
        :title="bindingPublicationPrice(group.preview.publications)"
        >{{ bindingPublicationPrice(group.preview.publications) }}</span
      >
      <span
        v-else-if="column.key === 'stock'"
        class="block truncate tabular-nums"
        :title="bindingPublicationStock(group.preview.publications)"
        >{{ bindingPublicationStock(group.preview.publications) }}</span
      >
      <Badge
        v-else-if="column.key === 'state'"
        :variant="
          group.preview.state === 'conflict'
            ? 'destructive'
            : group.preview.state === 'linked'
              ? 'secondary'
              : 'outline'
        "
        >{{ bindingStates[group.preview.state] }}</Badge
      >
      <Button
        v-else-if="column.key === 'matched'"
        type="button"
        variant="ghost"
        size="sm"
        :disabled="busy"
        aria-label="Открыть сопоставления"
        class="h-auto px-0 tabular-nums"
        :title="`Пар: ${group.preview.matchedCount} · Позиций товара: ${group.preview.catalogCount} · Публикаций: ${group.preview.publicationCount}`"
        @click="emit('edit', group)"
        >{{ group.preview.matchedCount }} /
        {{ group.preview.catalogCount }}</Button
      >
      <PublicationActions
        v-else-if="column.key === 'actions'"
        :busy="busy"
        :publication-disabled="!canOpen(group)"
        can-sync-stock
        @stock="emit('stock', group)"
        :catalog-targets="[
          {
            id: group.catalogRootId,
            label: group.preview.catalogRoot?.title ?? 'Товар без названия',
          },
        ]"
        :unlink-targets="[{ id: group.id, label: title(group) }]"
        @publication="emit('publication', group)"
        @catalog="emit('catalog', $event)"
        @unlink="emit('remove', group)"
      />
    </template>
  </DataTable>
</template>
