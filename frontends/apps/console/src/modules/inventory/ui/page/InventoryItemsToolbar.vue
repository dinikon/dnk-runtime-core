<script setup lang="ts">
import { Search, X } from "@lucide/vue";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";

defineProps<{ search: string; total?: number }>();
const emit = defineEmits<{ search: [value: string]; submit: []; clear: [] }>();
</script>

<template>
  <div class="flex shrink-0 flex-wrap items-center justify-between gap-3">
    <form
      role="search"
      aria-label="Поиск складской номенклатуры"
      class="w-full sm:max-w-md"
      @submit.prevent="emit('submit')"
    >
      <InputGroup>
        <InputGroupInput
          :model-value="search"
          type="search"
          aria-label="Поиск по SKU"
          placeholder="Поиск по SKU"
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
    <p
      v-if="total !== undefined"
      class="text-sm tabular-nums text-muted-foreground"
    >
      Найдено позиций: {{ total }}
    </p>
  </div>
</template>
