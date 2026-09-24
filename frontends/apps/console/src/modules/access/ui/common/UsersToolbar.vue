<script setup lang="ts">
import { Search } from "@lucide/vue";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UsersTab } from "../../model/access.types";

defineProps<{
  tab: UsersTab;
  search: string;
  role: string;
  status: string;
}>();
const emit = defineEmits<{
  "update:search": [value: string];
  "update:role": [value: string];
  "update:status": [value: string];
}>();
</script>

<template>
  <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem_12rem]">
    <div class="relative">
      <Search
        class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        :model-value="search"
        class="pl-9"
        :placeholder="
          tab === 'members' ? 'Поиск по имени или email' : 'Поиск по email'
        "
        @update:model-value="emit('update:search', String($event))"
      />
    </div>
    <Select
      :model-value="role"
      @update:model-value="emit('update:role', String($event))"
    >
      <SelectTrigger aria-label="Фильтр по роли">
        <SelectValue placeholder="Все роли" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectItem value="all">Все роли</SelectItem>
          <SelectItem value="admin">Администраторы</SelectItem>
          <SelectItem value="member">Участники</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
    <Select
      :model-value="status"
      @update:model-value="emit('update:status', String($event))"
    >
      <SelectTrigger aria-label="Фильтр по статусу">
        <SelectValue placeholder="Все статусы" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup v-if="tab === 'members'">
          <SelectItem value="all">Все статусы</SelectItem>
          <SelectItem value="active">Активные</SelectItem>
          <SelectItem value="revoked">Доступ отозван</SelectItem>
        </SelectGroup>
        <SelectGroup v-else>
          <SelectItem value="all">Все статусы</SelectItem>
          <SelectItem value="pending">Ожидают</SelectItem>
          <SelectItem value="accepted">Приняты</SelectItem>
          <SelectItem value="expired">Истекли</SelectItem>
          <SelectItem value="revoked">Отозваны</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
  </div>
</template>
