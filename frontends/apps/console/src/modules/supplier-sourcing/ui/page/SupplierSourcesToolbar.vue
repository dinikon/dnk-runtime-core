<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { SourcesParams } from "../../model/supplier-source.types";
defineProps<{
  params: SourcesParams;
  search: string;
  supplierSearch: string;
  supplierOptions: readonly { id: string; modelKey: string; name: string }[];
  suppliersLoading: boolean;
  suppliersError: string;
  supplierOffset: number;
  suppliersTotal: number;
  total?: number;
}>();
const emit = defineEmits<{
  search: [value: string];
  change: [value: Partial<SourcesParams>];
  clear: [];
  supplierSearch: [value: string];
  supplierPage: [offset: number];
  supplierRetry: [];
}>();
</script>
<template>
  <div
    class="flex min-w-0 flex-col gap-3 [&_[data-slot=native-select-wrapper]]:w-full"
  >
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Input
        type="search"
        :model-value="search"
        placeholder="Название или внешний код"
        aria-label="Поиск источников"
        @update:model-value="emit('search', String($event))"
      /><NativeSelect
        aria-label="Активность источников"
        :model-value="params.activity"
        @update:model-value="
          emit('change', {
            activity:
              $event === 'active' || $event === 'inactive' ? $event : 'all',
          })
        "
        ><NativeSelectOption value="all">Любая активность</NativeSelectOption
        ><NativeSelectOption value="active">Активные</NativeSelectOption
        ><NativeSelectOption value="inactive"
          >Неактивные</NativeSelectOption
        ></NativeSelect
      ><NativeSelect
        aria-label="Режим исполнения"
        :model-value="params.fulfillmentMode"
        @update:model-value="
          emit('change', {
            fulfillmentMode:
              $event === 'DROPSHIP' || $event === 'PURCHASE_TO_WAREHOUSE'
                ? $event
                : 'all',
          })
        "
        ><NativeSelectOption value="all">Все режимы</NativeSelectOption
        ><NativeSelectOption value="DROPSHIP">Дропшиппинг</NativeSelectOption
        ><NativeSelectOption value="PURCHASE_TO_WAREHOUSE"
          >Закупка на склад</NativeSelectOption
        ></NativeSelect
      ><Button variant="outline" @click="emit('clear')"
        >Сбросить фильтры</Button
      >
    </div>
    <details class="rounded-md border p-3">
      <summary class="cursor-pointer text-sm">
        Поставщик{{ params.supplierModelKey ? " · фильтр включён" : "" }}
      </summary>
      <div class="mt-3 flex flex-col gap-2 sm:max-w-lg">
        <NativeSelect
          aria-label="Тип поставщика для фильтра"
          :model-value="params.supplierModelKey"
          @update:model-value="
            emit('change', {
              supplierModelKey:
                $event === 'crm.company' || $event === 'crm.contact'
                  ? $event
                  : '',
              supplierId: '',
            })
          "
          ><NativeSelectOption value=""
            >Все типы контрагентов</NativeSelectOption
          ><NativeSelectOption value="crm.company">Компании</NativeSelectOption
          ><NativeSelectOption value="crm.contact"
            >Контакты</NativeSelectOption
          ></NativeSelect
        >
        <p
          v-if="!params.supplierModelKey"
          class="text-sm text-muted-foreground"
        >
          Выберите тип для поиска конкретного контрагента.
        </p>
        <template v-if="params.supplierModelKey">
          <Input
            :model-value="supplierSearch"
            aria-label="Найти контрагента для фильтра"
            placeholder="Поиск контрагента поставщика"
            @update:model-value="emit('supplierSearch', String($event))"
          /><NativeSelect
            aria-label="Фильтр по поставщику"
            :model-value="params.supplierId"
            @update:model-value="
              emit('change', { supplierId: String($event ?? '') })
            "
            ><NativeSelectOption value="">Все поставщики</NativeSelectOption
            ><NativeSelectOption
              v-if="
                params.supplierId &&
                !supplierOptions.some((item) => item.id === params.supplierId)
              "
              :value="params.supplierId"
              >Выбранный поставщик · {{ params.supplierId }}</NativeSelectOption
            ><NativeSelectOption
              v-for="supplier in supplierOptions"
              :key="`${supplier.modelKey}:${supplier.id}`"
              :value="supplier.id"
              >{{ supplier.name }}</NativeSelectOption
            ></NativeSelect
          >
          <p v-if="suppliersLoading" role="status" class="text-sm">
            Поиск контрагентов…
          </p>
          <p
            v-if="suppliersError"
            role="alert"
            class="text-sm text-destructive"
          >
            {{ suppliersError }}
            <Button size="sm" variant="outline" @click="emit('supplierRetry')"
              >Повторить</Button
            >
          </p>
          <div v-if="suppliersTotal > 20" class="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              :disabled="suppliersLoading || !supplierOffset"
              @click="emit('supplierPage', Math.max(0, supplierOffset - 20))"
              >Предыдущие контрагенты</Button
            ><Button
              size="sm"
              variant="outline"
              :disabled="
                suppliersLoading || supplierOffset + 20 >= suppliersTotal
              "
              @click="emit('supplierPage', supplierOffset + 20)"
              >Следующие контрагенты</Button
            >
          </div>
        </template>
      </div>
    </details>
    <p v-if="total !== undefined" class="text-sm text-muted-foreground">
      Найдено источников: {{ total }}
    </p>
  </div>
</template>
