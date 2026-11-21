<script setup lang="ts">
import type { ReturnOriginLine } from "../../model/return-origin.types";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { computed } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type {
  ReturnAllocation,
  ReturnPreparation,
  ReturnExecutionValues,
  ReturnExecutionErrors,
} from "../../model/return-posting.types";
import { returnBaseTotal } from "../../model/return-execution";
const props = defineProps<{
  values: ReturnExecutionValues;
  context: ReturnPreparation | undefined;
  errors: ReturnExecutionErrors;
  disabled: boolean;
  uoms: readonly { code: string; dimension: string }[];
  uomError: string;
  origins: readonly ReturnOriginLine[];
}>();
const emit = defineEmits<{
  change: [key: string, row: ReturnAllocation];
  select: [id: string, selected: boolean];
  split: [key: string];
  remove: [key: string];
  pick: [key: string];
  destination: [key: string];
  retryUnits: [];
}>();
const groups = computed(() => {
  const map = new Map<string, ReturnAllocation[]>();
  for (const row of props.values.rows) {
    const group = map.get(row.documentLineId) ?? [];
    group.push(row);
    map.set(row.documentLineId, group);
  }
  return [...map.entries()]
    .map(([id, rows]) => ({
      id,
      line: rows[0]!,
      rows,
      current: props.context?.lines.find((v) => v.documentLineId === id),
    }))
    .sort((a, b) => a.line.position - b.line.position);
});
function units(
  row: ReturnAllocation,
): readonly { code: string; dimension: string }[] {
  const dimension = props.uoms.find((v) => v.code === row.baseUom)?.dimension;
  return props.uoms.filter((v) => v.dimension === dimension);
}
</script>
<template>
  <div class="flex min-w-0 flex-col gap-4" aria-label="Распределения возврата">
    <p v-if="errors.form" role="alert" class="text-sm text-destructive">
      {{ errors.form }}
    </p>
    <p v-if="uomError" role="alert" class="text-sm text-destructive">
      {{ uomError
      }}<Button type="button" variant="outline" @click="emit('retryUnits')"
        >Повторить загрузку единиц</Button
      >
    </p>
    <section
      v-for="group in groups"
      :key="group.id"
      :aria-label="`Строка возврата ${group.line.position + 1}: ${group.line.sku}`"
      class="min-w-0 rounded-lg border p-4"
    >
      <header class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <h2 class="break-words font-medium">
            Строка {{ group.line.position + 1 }} · {{ group.line.sku }}
          </h2>
          <dl class="mt-2 grid grid-cols-3 gap-3 text-sm">
            <div>
              <dt class="text-xs text-muted-foreground">Запланировано</dt>
              <dd class="break-all">
                {{ group.line.plannedQuantity }} {{ group.line.baseUom }}
              </dd>
            </div>
            <div>
              <dt class="text-xs text-muted-foreground">Выполнено</dt>
              <dd class="break-all">
                {{ group.line.executedQuantity }} {{ group.line.baseUom }}
              </dd>
            </div>
            <div>
              <dt class="text-xs text-muted-foreground">Осталось</dt>
              <dd class="break-all font-medium">
                {{ group.line.remainingQuantity }} {{ group.line.baseUom }}
              </dd>
            </div>
          </dl>
          <p
            v-if="
              group.current &&
              group.current.remainingQuantity !== group.line.remainingQuantity
            "
            class="mt-2 text-sm text-destructive"
          >
            Сейчас на сервере выполнено {{ group.current.executedQuantity }},
            осталось {{ group.current.remainingQuantity }}
            {{ group.current.baseUom }}.
          </p>
        </div>
        <label class="flex items-center gap-2 text-sm"
          ><input
            type="checkbox"
            :checked="group.rows.some((row) => row.selected)"
            :disabled="
              disabled ||
              !/[1-9]/.test(group.line.remainingQuantity.split(/[eE]/)[0] ?? '')
            "
            @change="
              emit(
                'select',
                group.id,
                ($event.target as HTMLInputElement).checked,
              )
            "
          />Обработать строку {{ group.line.position + 1 }}</label
        >
      </header>
      <template v-if="group.rows.some((row) => row.selected)">
        <p class="my-3 text-xs text-muted-foreground">
          {{
            returnBaseTotal(group.rows) !== null
              ? `В этом возврате: ${returnBaseTotal(group.rows)} ${group.line.baseUom}.`
              : "Пересчёт единиц и общий лимит проверит сервер."
          }}
        </p>
        <section
          v-for="(row, index) in group.rows"
          :key="row.key"
          :aria-label="`Распределение ${index + 1}`"
          class="mt-3 min-w-0 rounded-md border p-3"
        >
          <div class="mb-3 flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              :disabled="
                disabled || values.rows.filter((v) => v.selected).length >= 500
              "
              @click="emit('split', row.key)"
              >{{
                row.trackingMode.includes("SERIAL")
                  ? "Ещё экземпляр"
                  : "Добавить распределение"
              }}</Button
            ><Button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="disabled"
              :aria-label="`Удалить распределение ${index + 1}`"
              @click="emit('remove', row.key)"
              >{{
                group.rows.length === 1
                  ? "Исключить строку"
                  : "Удалить распределение"
              }}</Button
            >
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm"
              >Количество<Input
                :model-value="row.quantity"
                type="text"
                inputmode="decimal"
                :readonly="row.trackingMode.includes('SERIAL')"
                :disabled="disabled"
                @update:model-value="
                  emit('change', row.key, { ...row, quantity: String($event) })
                "
            /></label>
            <label class="text-sm"
              >Единица<select
                aria-label="Единица"
                :value="row.uom"
                :disabled="disabled || row.trackingMode.includes('SERIAL')"
                class="mt-1 h-9 w-full rounded-md border bg-background px-2"
                @change="
                  emit('change', row.key, {
                    ...row,
                    uom: ($event.target as HTMLSelectElement).value,
                  })
                "
              >
                <option
                  v-for="unit in units(row)"
                  :key="unit.code"
                  :value="unit.code"
                >
                  {{ unit.code }}
                </option>
              </select></label
            >
          </div>
          <div
            v-if="row.direction === 'FROM_RECIPIENT'"
            class="mt-3 space-y-3 rounded-md bg-muted p-3"
          >
            <p class="break-words text-sm">
              Адрес приёмки:
              {{
                row.destination
                  ? `${row.destination.code} — ${row.destination.name}`
                  : "Не выбран"
              }}
            </p>
            <Button
              type="button"
              variant="outline"
              :disabled="disabled"
              @click="emit('destination', row.key)"
              >Выбрать адрес приёмки</Button
            >
            <label class="block text-sm"
              >Состояние приёмки<select
                aria-label="Состояние приёмки"
                class="mt-2 h-10 w-full rounded-md border bg-background px-3"
                :value="row.stockStatus"
                :disabled="disabled"
                @change="
                  emit('change', row.key, {
                    ...row,
                    stockStatus: ($event.target as HTMLSelectElement).value,
                  })
                "
              >
                <option value="" disabled>Выберите состояние</option>
                <option
                  v-for="state in [
                    'SELLABLE',
                    'QUARANTINE',
                    'DAMAGED',
                    'BLOCKED',
                  ]"
                  :key="state"
                  :value="state"
                >
                  {{ stockStatusLabel(state) }}
                </option>
              </select></label
            >
            <p
              v-if="
                origins.find((v) => v.id === row.originExecutionLineId)
                  ?.lotNumber
              "
              class="text-sm"
            >
              Партия:
              {{
                origins.find((v) => v.id === row.originExecutionLineId)
                  ?.lotNumber
              }}
            </p>
            <p
              v-if="
                origins.find((v) => v.id === row.originExecutionLineId)
                  ?.serialNumber
              "
              class="text-sm"
            >
              Серия:
              {{
                origins.find((v) => v.id === row.originExecutionLineId)
                  ?.serialNumber
              }}
            </p>
          </div>
          <div v-else class="mt-3 min-w-0 rounded-md bg-muted p-3">
            <template v-if="row.source"
              ><p class="break-words text-sm">
                Источник: {{ row.source.locationCode }} ·
                {{ stockStatusLabel(row.source.stockStatus) }}
              </p>
              <p class="mt-1 text-sm">
                Физическое количество по последним сведениям:
                <strong
                  >{{ row.source.onHandQuantity }}
                  {{ row.source.baseUom }}</strong
                >
              </p>
              <p v-if="row.source.lotNumber" class="mt-1 break-words text-sm">
                Партия: {{ row.source.lotNumber }} · производство
                {{ row.source.manufacturedOn ?? "—" }} · срок
                {{ row.source.expiresOn ?? "—" }}
              </p>
              <p
                v-if="row.source.serialNumber"
                class="mt-1 break-words text-sm"
              >
                Серия: {{ row.source.serialNumber }}
              </p></template
            >
            <p v-else class="text-sm text-muted-foreground">
              Исходная позиция не выбрана.
            </p>
            <p
              v-if="row.sourceMissing"
              role="alert"
              class="mt-2 text-sm text-destructive"
            >
              Источник больше не найден среди допустимых позиций. Сохранён
              предыдущий выбор для сверки.
            </p>
            <Button
              type="button"
              variant="outline"
              class="mt-2"
              :disabled="disabled"
              @click="emit('pick', row.key)"
              >Выбрать позицию</Button
            >
          </div>
          <p class="mt-2 text-xs text-muted-foreground">
            По исходному факту: {{ row.originalQuantity }} · Возвращено:
            {{ row.returnedQuantity }} · К возврату:
            {{ row.returnableQuantity }} {{ row.baseUom }}
          </p>
          <p
            v-if="errors.rows[row.key]"
            role="alert"
            class="mt-3 text-sm text-destructive"
          >
            {{ errors.rows[row.key] }}
          </p>
        </section>
      </template>
      <p v-else class="mt-3 text-sm text-muted-foreground">
        Строка исключена из этого возврата. Ввод сохранён.
      </p>
      <p
        v-if="errors.lines[group.id]"
        role="alert"
        class="mt-3 text-sm text-destructive"
      >
        {{ errors.lines[group.id] }}
      </p>
    </section>
  </div>
</template>
