<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  bindingModes,
  bindingStates,
  type CatalogBinding,
} from "../../model/bindings/binding.types";
import BindingPositionCell from "./BindingPositionCell.vue";
defineProps<{ items: CatalogBinding[]; busy: boolean }>();
const emit = defineEmits<{
  edit: [group: CatalogBinding];
  remove: [group: CatalogBinding];
  catalog: [id: string];
  publication: [group: CatalogBinding];
}>();
</script>
<template>
  <ul class="divide-y border-y">
    <li v-for="group in items" :key="group.id" class="space-y-3 py-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="font-medium">
            {{ group.channelName }} · {{ bindingModes[group.mode] }}
          </p>
          <p class="text-muted-foreground text-xs">
            Группа {{ group.id.slice(0, 8) }} ·
            {{ group.preview.matchedCount }} пар · Catalog:
            {{ group.preview.catalogCount }} · Площадка:
            {{ group.preview.publicationCount }}
          </p>
        </div>
        <Badge
          :variant="
            group.preview.state === 'conflict' ? 'destructive' : 'secondary'
          "
          >{{ bindingStates[group.preview.state] }}</Badge
        >
      </div>
      <BindingPositionCell
        v-if="group.preview.catalogRoot"
        :position="group.preview.catalogRoot"
      />
      <div class="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          @click="emit('catalog', group.catalogRootId)"
          >Открыть Catalog</Button
        ><Button size="sm" variant="outline" @click="emit('publication', group)"
          >Открыть публикацию</Button
        ><Button
          size="sm"
          variant="outline"
          :disabled="busy"
          @click="emit('edit', group)"
          >Сопоставления</Button
        ><Button
          size="sm"
          variant="ghost"
          :disabled="busy"
          @click="emit('remove', group)"
          >Снять связь</Button
        >
      </div>
    </li>
  </ul>
</template>
