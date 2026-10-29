<script setup lang="ts">
import { computed } from "vue";
import { Ellipsis, ExternalLink, Link2, Package, Unlink } from "@lucide/vue";
import { DataTable } from "@/components/custom-ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  edit: [group: CatalogBinding];
  remove: [group: CatalogBinding];
  catalog: [id: string];
  publication: [group: CatalogBinding];
}>();
const columns = computed(() =>
  bindingGroupsColumns.filter(
    (column) => props.showCatalog || column.key !== "catalog",
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
      <span
        v-else-if="column.key === 'matched'"
        class="tabular-nums"
        :title="`Пар: ${group.preview.matchedCount} · Позиций товара: ${group.preview.catalogCount} · Публикаций: ${group.preview.publicationCount}`"
        >{{ group.preview.matchedCount }} /
        {{ group.preview.catalogCount }}</span
      >
      <DropdownMenu v-else-if="column.key === 'actions'">
        <DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="busy"
            :aria-label="`Действия: ${group.channelName} · ${title(group)}`"
            ><Ellipsis /></Button
        ></DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-56"
          ><DropdownMenuGroup>
            <DropdownMenuItem
              :disabled="!canOpen(group)"
              @select="emit('publication', group)"
              ><ExternalLink />Открыть публикацию</DropdownMenuItem
            >
            <DropdownMenuItem
              v-if="showCatalog"
              @select="emit('catalog', group.catalogRootId)"
              ><Package />Открыть товар</DropdownMenuItem
            >
            <DropdownMenuItem @select="emit('edit', group)"
              ><Link2 />Сопоставления</DropdownMenuItem
            > </DropdownMenuGroup
          ><DropdownMenuSeparator /><DropdownMenuGroup
            ><DropdownMenuItem
              variant="destructive"
              @select="emit('remove', group)"
              ><Unlink />Снять связь</DropdownMenuItem
            ></DropdownMenuGroup
          ></DropdownMenuContent
        >
      </DropdownMenu>
    </template>
  </DataTable>
</template>
