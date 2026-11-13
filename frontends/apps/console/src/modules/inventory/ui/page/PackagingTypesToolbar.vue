<script setup lang="ts">
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { PackagingTypeActivity } from "../../model/packaging-type.types";
import { Search, X } from "@lucide/vue";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";

defineProps<{
  search: string;
  activity: PackagingTypeActivity;
  total?: number;
}>();
const emit = defineEmits<{
  search: [value: string];
  submit: [];
  clear: [];
  activity: [value: PackagingTypeActivity];
}>();
</script>

<template>
  <div class="flex shrink-0 flex-wrap items-center justify-between gap-3">
    <form
      role="search"
      aria-label="Поиск типов тары"
      class="w-full sm:max-w-md"
      @submit.prevent="emit('submit')"
    >
      <InputGroup>
        <InputGroupInput
          :model-value="search"
          type="search"
          aria-label="Поиск по коду или названию"
          placeholder="Поиск по коду или названию"
          @update:model-value="emit('search', String($event))"
        />
        <InputGroupAddon><Search aria-hidden="true" /></InputGroupAddon>
        <InputGroupAddon v-if="search" align="inline-end">
          <InputGroupButton
            type="button"
            size="icon-xs"
            aria-label="Очистить поиск"
            @click="emit('clear')"
            ><X aria-hidden="true"
          /></InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
    </form>
    <ToggleGroup
      type="single"
      variant="outline"
      :model-value="activity"
      aria-label="Активность типов тары"
      @update:model-value="
        emit(
          'activity',
          $event === 'active'
            ? 'active'
            : $event === 'inactive'
              ? 'inactive'
              : 'all',
        )
      "
    >
      <ToggleGroupItem value="all">Все</ToggleGroupItem>
      <ToggleGroupItem value="active">Активные</ToggleGroupItem>
      <ToggleGroupItem value="inactive">Неактивные</ToggleGroupItem>
    </ToggleGroup>
    <p
      v-if="total !== undefined"
      class="text-sm tabular-nums text-muted-foreground"
    >
      Найдено типов тары: {{ total }}
    </p>
  </div>
</template>
