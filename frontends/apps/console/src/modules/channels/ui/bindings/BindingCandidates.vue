<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import OffsetPagination from "@/shared/pagination/OffsetPagination.vue";
import BindingPositionCell from "./BindingPositionCell.vue";
import type { BindingCandidates } from "../../model/bindings/binding.types";
defineProps<{
  title: string;
  page?: BindingCandidates;
  pending: boolean;
  error: string;
  search: string;
  offset: number;
  limit: number;
  allowedIds?: string[];
  busy?: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  choose: [id: string];
  paginate: [page: number, limit: number];
  retry: [];
}>();
</script>
<template>
  <section class="space-y-3">
    <h3 class="font-medium">{{ title }}</h3>
    <Input
      :model-value="search"
      :disabled="busy"
      :aria-label="`Поиск: ${title}`"
      placeholder="Название или артикул"
      @update:model-value="emit('search', String($event))"
    />
    <p v-if="pending" class="text-sm text-muted-foreground" role="status">
      Загрузка…
    </p>
    <div v-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
      <Button variant="outline" size="sm" @click="emit('retry')"
        >Повторить</Button
      >
    </div>
    <ul v-if="page" class="divide-y border-y">
      <li
        v-for="position in page.items"
        :key="position.id"
        class="flex items-center justify-between gap-3 py-3"
      >
        <BindingPositionCell :position="position" /><Button
          size="sm"
          variant="outline"
          :disabled="
            busy ||
            (page.occupiedIds.includes(position.id) &&
              !allowedIds?.includes(position.id))
          "
          @click="emit('choose', position.id)"
          >{{
            busy ||
            (page.occupiedIds.includes(position.id) &&
              !allowedIds?.includes(position.id))
              ? "Занята"
              : "Выбрать"
          }}</Button
        >
      </li>
      <li v-if="!page.items.length" class="py-6 text-sm text-muted-foreground">
        Подходящих позиций нет.
      </li>
    </ul>
    <OffsetPagination
      :total="page?.total ?? 0"
      :page="Math.floor(offset / limit) + 1"
      :limit="limit"
      :limit-options="[25, 50, 100]"
      locale="ru"
      :disabled="busy || pending || !page"
      @change="emit('paginate', $event.page, $event.limit)"
    />
  </section>
</template>
