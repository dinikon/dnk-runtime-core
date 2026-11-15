<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import InventorySkuPicker from "./InventorySkuPicker.vue";
import type { InventorySkuOption } from "../../model/inventory-sku.types";
import type {
  ReceiptDraftLine,
  ReceiptErrors,
} from "../../model/receipt.types";
const props = defineProps<{
  lines: readonly ReceiptDraftLine[];
  errors: ReceiptErrors;
  disabled: boolean;
  activeKey: string;
  search: string;
  options: readonly InventorySkuOption[];
  loading: boolean;
  error: string;
  total: number;
  uoms: readonly { code: string; dimension: string }[];
}>();
const emit = defineEmits<{
  change: [key: string, value: ReceiptDraftLine];
  add: [];
  remove: [key: string];
  search: [key: string, value: string];
  select: [key: string, value: InventorySkuOption];
  clear: [key: string];
  retry: [];
}>();
function units(
  line: ReceiptDraftLine,
): readonly { code: string; dimension: string }[] {
  const dim = props.uoms.find((u) => u.code === line.baseUom)?.dimension;
  return dim ? props.uoms.filter((u) => u.dimension === dim) : [];
}
</script>
<template>
  <fieldset class="flex min-w-0 flex-col gap-4" :disabled="disabled">
    <legend class="mb-3 text-lg font-semibold">Плановые строки</legend>
    <p class="text-sm text-muted-foreground">
      Пустой черновик допустим. Локации, партии и серийные экземпляры выбираются
      при фактической приёмке.
    </p>
    <p v-if="errors.lines" role="alert" class="text-sm text-destructive">
      {{ errors.lines }}
    </p>
    <section
      v-for="(line, index) in lines"
      :key="line.key"
      class="min-w-0 rounded-md border p-3"
      :aria-label="`Плановая строка ${index + 1}`"
    >
      <header class="mb-3 flex items-center justify-between gap-2">
        <h3 class="text-sm font-medium">Строка {{ index + 1 }}</h3>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          :disabled="disabled"
          :aria-label="`Удалить строку ${index + 1}`"
          @click="emit('remove', line.key)"
          >Удалить</Button
        >
      </header>
      <label
        :for="`receipt-sku-${line.key}`"
        class="mb-1 block text-sm font-medium"
        >SKU</label
      >
      <p
        v-if="line.id"
        :id="`receipt-sku-${line.key}`"
        class="rounded-md bg-muted p-2 font-mono text-sm"
      >
        {{ line.sku
        }}<span class="ml-2 font-sans text-xs text-muted-foreground"
          >Сохранённая строка</span
        >
      </p>
      <InventorySkuPicker
        v-else
        :id="`receipt-sku-${line.key}`"
        :search="activeKey === line.key ? search : ''"
        :options="options"
        :loading="loading"
        :error="error"
        :total="total"
        :selected-id="line.inventoryItemId"
        :selected-code="line.sku"
        :disabled="disabled"
        :allow-create="false"
        @search="emit('search', line.key, $event)"
        @select="emit('select', line.key, $event)"
        @clear="emit('clear', line.key)"
        @retry="emit('retry')"
      />
      <p
        v-if="errors.lineFields[line.key]?.inventoryItemId"
        role="alert"
        class="text-sm text-destructive"
      >
        {{ errors.lineFields[line.key]?.inventoryItemId }}
      </p>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label
            :for="`receipt-quantity-${line.key}`"
            class="mb-1 block text-sm font-medium"
            >Количество</label
          ><Input
            :id="`receipt-quantity-${line.key}`"
            :model-value="line.quantity"
            type="text"
            inputmode="decimal"
            autocomplete="off"
            :aria-invalid="!!errors.lineFields[line.key]?.quantity"
            @update:model-value="
              emit('change', line.key, { ...line, quantity: String($event) })
            "
          />
          <p
            v-if="errors.lineFields[line.key]?.quantity"
            role="alert"
            class="text-sm text-destructive"
          >
            {{ errors.lineFields[line.key]?.quantity }}
          </p>
        </div>
        <div>
          <label
            :for="`receipt-uom-${line.key}`"
            class="mb-1 block text-sm font-medium"
            >Единица</label
          ><select
            :id="`receipt-uom-${line.key}`"
            :value="line.uom"
            :disabled="disabled || !line.inventoryItemId || !units(line).length"
            class="h-9 w-full rounded-md border bg-background px-2 text-sm"
            @change="
              emit('change', line.key, {
                ...line,
                uom: ($event.target as HTMLSelectElement).value,
              })
            "
          >
            <option v-if="!line.uom" value="">Выберите SKU</option>
            <option
              v-for="uom in units(line)"
              :key="uom.code"
              :value="uom.code"
            >
              {{ uom.code }}
            </option>
          </select>
          <p class="mt-1 text-xs text-muted-foreground">
            Базовая единица: {{ line.baseUom || "—" }}. Пересчёт сохраняет
            сервер.
          </p>
          <p
            v-if="errors.lineFields[line.key]?.uom"
            role="alert"
            class="text-sm text-destructive"
          >
            {{ errors.lineFields[line.key]?.uom }}
          </p>
        </div>
      </div>
      <p
        v-if="errors.lineFields[line.key]?.error"
        role="alert"
        class="mt-2 text-sm text-destructive"
      >
        {{ errors.lineFields[line.key]?.error }}
      </p>
    </section>
    <Button
      type="button"
      variant="outline"
      class="self-start"
      :disabled="disabled || lines.length >= 100"
      @click="emit('add')"
      >Добавить строку</Button
    >
  </fieldset>
</template>
