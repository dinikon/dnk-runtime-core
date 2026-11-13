<script setup lang="ts">
import { Search, X } from "@lucide/vue";
import {
  InputGroup,
  InputGroupInput,
  InputGroupAddon,
  InputGroupButton,
} from "@/components/ui/input-group";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import StockLocationTypeSelect from "../forms/StockLocationTypeSelect.vue";
import type {
  StockLocationActivity,
  StockLocationType,
} from "../../model/stock-location.types";
defineProps<{
  search: string;
  activity: StockLocationActivity;
  locationType: StockLocationType | null;
  total?: number;
}>();
const emit = defineEmits<{
  search: [value: string];
  submit: [];
  clear: [];
  activity: [value: StockLocationActivity];
  type: [value: StockLocationType | null];
}>();
</script>
<template>
  <div class="flex shrink-0 flex-col gap-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <form
        role="search"
        aria-label="Поиск локаций"
        class="w-full sm:max-w-md"
        @submit.prevent="emit('submit')"
      >
        <InputGroup
          ><InputGroupInput
            :model-value="search"
            type="search"
            aria-label="Поиск локаций по коду или названию"
            placeholder="Поиск по коду или названию"
            @update:model-value="
              emit('search', String($event))
            " /><InputGroupAddon><Search aria-hidden="true" /></InputGroupAddon
          ><InputGroupAddon v-if="search" align="inline-end"
            ><InputGroupButton
              type="button"
              size="icon-xs"
              aria-label="Очистить поиск локаций"
              @click="emit('clear')"
              ><X aria-hidden="true" /></InputGroupButton></InputGroupAddon
        ></InputGroup>
      </form>
      <p
        v-if="total !== undefined"
        class="text-sm tabular-nums text-muted-foreground"
      >
        Найдено локаций: {{ total }}
      </p>
    </div>
    <FieldGroup class="grid grid-cols-2 gap-3 md:grid-cols-3">
      <Field class="col-span-2 md:col-span-1"
        ><FieldLabel id="stock-locations-activity-label">Активность</FieldLabel
        ><ToggleGroup
          type="single"
          variant="outline"
          :model-value="activity"
          aria-labelledby="stock-locations-activity-label"
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
          ><ToggleGroupItem value="all">Все</ToggleGroupItem
          ><ToggleGroupItem value="active">Активные</ToggleGroupItem
          ><ToggleGroupItem value="inactive"
            >Неактивные</ToggleGroupItem
          ></ToggleGroup
        ></Field
      >
      <Field
        ><FieldLabel for="stock-locations-type">Тип</FieldLabel
        ><StockLocationTypeSelect
          id="stock-locations-type"
          label="Фильтр типа локаций"
          :value="locationType"
          allow-all
          @change="emit('type', $event)"
      /></Field>
      <Field
        ><FieldLabel for="stock-locations-parent">Родитель</FieldLabel
        ><slot name="parent"
      /></Field>
    </FieldGroup>
  </div>
</template>
