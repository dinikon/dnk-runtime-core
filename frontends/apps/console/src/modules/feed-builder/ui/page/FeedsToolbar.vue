<script setup lang="ts">
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import type { FeedFilters } from "../../model/feed.types";
import { feedStatuses } from "../../model/feed.constants";
defineProps<{ filters: FeedFilters }>();
defineEmits<{ filter: [key: "search" | "status", value: string] }>();
</script>
<template>
  <div class="flex shrink-0 flex-col gap-3 sm:flex-row">
    <Input
      :model-value="filters.search"
      class="sm:max-w-sm"
      type="search"
      placeholder="Поиск по названию или коду"
      aria-label="Поиск фидов"
      maxlength="255"
      @update:model-value="$emit('filter', 'search', String($event))"
    />
    <Select
      :model-value="filters.status || 'working'"
      @update:model-value="
        $emit('filter', 'status', $event === 'working' ? '' : String($event))
      "
    >
      <SelectTrigger class="w-full sm:w-52" aria-label="Статус фида"
        ><SelectValue
      /></SelectTrigger>
      <SelectContent
        ><SelectGroup
          ><SelectItem value="working">Все рабочие</SelectItem
          ><SelectItem
            v-for="(label, status) in feedStatuses"
            :key="status"
            :value="status"
            >{{ label }}</SelectItem
          ></SelectGroup
        ></SelectContent
      >
    </Select>
  </div>
</template>
