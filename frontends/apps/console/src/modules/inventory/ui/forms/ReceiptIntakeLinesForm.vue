<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type {
  IntakeRow,
  ReceiptReferenceKind,
  ReceiptIntakeErrors,
} from "../../model/receipt-posting.types";
import { serialTracking, lotTracking } from "../../model/receipt-intake";
const props = defineProps<{
  rows: readonly IntakeRow[];
  disabled: boolean;
  errors: ReceiptIntakeErrors;
  uoms: readonly { code: string; dimension: string }[];
}>();
const emit = defineEmits<{
  change: [key: string, row: IntakeRow];
  remove: [key: string];
  split: [key: string];
  pick: [key: string, kind: ReceiptReferenceKind];
}>();
function units(row: IntakeRow): readonly { code: string; dimension: string }[] {
  const dim = props.uoms.find((u) => u.code === row.baseUom)?.dimension;
  return props.uoms.filter((u) => u.dimension === dim);
}
</script>
<template>
  <fieldset class="flex min-w-0 flex-col gap-4" :disabled="disabled">
    <legend class="mb-3 text-lg font-semibold">Фактические строки</legend>
    <p v-if="errors.form" role="alert" class="text-destructive">
      {{ errors.form }}
    </p>
    <section
      v-for="(row, index) in rows"
      :key="row.key"
      :aria-label="`Фактическая строка ${index + 1}`"
      class="min-w-0 rounded-lg border p-4"
    >
      <header class="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 class="font-mono font-medium">{{ row.sku }}</h2>
          <p class="text-xs text-muted-foreground">
            Осталось по строке плана: {{ row.remainingQuantity }}
            {{ row.baseUom }} · {{ row.trackingMode }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled || rows.length >= 500"
            @click="emit('split', row.key)"
            >{{
              serialTracking(row) ? "Ещё экземпляр" : "Разделить строку"
            }}</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="disabled"
            :aria-label="`Исключить факт ${index + 1}`"
            @click="emit('remove', row.key)"
            >Исключить</Button
          >
        </div>
      </header>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="text-sm"
          >Количество<Input
            :model-value="row.quantity"
            type="text"
            inputmode="decimal"
            :readonly="serialTracking(row)"
            :disabled="disabled"
            @update:model-value="
              emit('change', row.key, { ...row, quantity: String($event) })
            "
        /></label>
        <label class="text-sm"
          >Единица<select
            :value="row.uom"
            :disabled="disabled || serialTracking(row) || !units(row).length"
            class="mt-1 h-9 w-full rounded-md border bg-background px-2"
            @change="
              emit('change', row.key, {
                ...row,
                uom: ($event.target as HTMLSelectElement).value,
              })
            "
          >
            <option v-for="uom in units(row)" :key="uom.code" :value="uom.code">
              {{ uom.code }}
            </option>
          </select></label
        >
        <div class="min-w-0">
          <p class="mb-1 text-sm">Локация</p>
          <p
            v-if="row.locationId"
            class="mb-1 break-words text-sm text-muted-foreground"
          >
            {{ row.locationLabel || row.locationId }}
          </p>
          <Button
            type="button"
            variant="outline"
            :disabled="disabled"
            @click="emit('pick', row.key, 'locations')"
            >Выбрать локацию</Button
          >
        </div>
        <label class="text-sm"
          >Состояние запаса<select
            :value="row.stockStatus"
            :disabled="disabled"
            class="mt-1 h-9 w-full rounded-md border bg-background px-2"
            @change="
              emit('change', row.key, {
                ...row,
                stockStatus: ($event.target as HTMLSelectElement)
                  .value as IntakeRow['stockStatus'],
              })
            "
          >
            <option value="SELLABLE">Пригодный к продаже</option>
            <option value="QUARANTINE">Карантин</option>
            <option value="DAMAGED">Повреждён</option>
            <option value="BLOCKED">Заблокирован</option>
          </select></label
        >
        <div v-if="lotTracking(row)" class="min-w-0">
          <p class="mb-1 text-sm">
            Партия:
            <span class="font-mono">{{ row.lotNumber || "не выбрана" }}</span>
          </p>
          <Button
            type="button"
            variant="outline"
            :disabled="disabled"
            @click="emit('pick', row.key, 'lots')"
            >Выбрать партию</Button
          >
          <p
            class="mt-2 text-xs"
            :class="
              row.expirationMode === 'REQUIRED' && !row.expiresOn
                ? 'text-destructive'
                : 'text-muted-foreground'
            "
          >
            Даты из партии: производство {{ row.manufacturedOn ?? "—" }}, срок
            {{ row.expiresOn ?? "не заполнен" }}.
          </p>
        </div>
        <div v-if="serialTracking(row)" class="min-w-0">
          <p class="mb-1 text-sm">
            Экземпляр:
            <span class="font-mono">{{ row.serialNumber || "не выбран" }}</span>
          </p>
          <Button
            type="button"
            variant="outline"
            :disabled="disabled"
            @click="emit('pick', row.key, 'serials')"
            >Выбрать экземпляр</Button
          >
          <p class="mt-2 text-xs text-muted-foreground">
            Один экземпляр — 1 PCS.
            {{
              row.trackingMode === "SERIAL"
                ? "Собственных дат у SERIAL нет."
                : "Партия должна совпадать с партией экземпляра."
            }}
          </p>
        </div>
      </div>
      <details class="mt-4 rounded-md bg-muted p-3">
        <summary class="cursor-pointer text-sm">
          Исходная стоимость фактической строки
        </summary>
        <label class="mt-3 flex items-center gap-2 text-sm"
          ><input
            type="checkbox"
            :checked="row.costKnown"
            :disabled="disabled"
            @change="
              emit('change', row.key, {
                ...row,
                costKnown: ($event.target as HTMLInputElement).checked,
              })
            "
          />Сумма известна</label
        >
        <p v-if="!row.costKnown" class="mt-2 text-xs text-muted-foreground">
          Стоимость неизвестна. Ноль не подставляется.
        </p>
        <div v-else class="mt-3 grid gap-3 sm:grid-cols-2">
          <label class="text-sm"
            >Полная сумма<Input
              :model-value="row.costAmount"
              type="text"
              inputmode="decimal"
              :disabled="disabled"
              @update:model-value="
                emit('change', row.key, { ...row, costAmount: String($event) })
              " /></label
          ><label class="text-sm"
            >Валюта<Input
              :model-value="row.costCurrency"
              maxlength="3"
              placeholder="USD"
              :disabled="disabled"
              @update:model-value="
                emit('change', row.key, {
                  ...row,
                  costCurrency: String($event).toUpperCase(),
                })
              " /></label
          ><label class="text-sm sm:col-span-2"
            >Ссылка на основание<Input
              :model-value="row.costReference"
              maxlength="200"
              :disabled="disabled"
              @update:model-value="
                emit('change', row.key, {
                  ...row,
                  costReference: String($event),
                })
              "
          /></label>
          <p class="text-xs text-muted-foreground sm:col-span-2">
            Сумма относится ко всему фактическому количеству этой строки. Явный
            ноль означает бесплатное поступление.
          </p>
        </div>
      </details>
      <p
        v-if="errors.rows[row.key]"
        role="alert"
        class="mt-3 text-sm text-destructive"
      >
        {{ errors.rows[row.key] }}
      </p>
    </section>
  </fieldset>
</template>
