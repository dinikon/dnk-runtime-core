<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { computed } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type {
  StatusChangeAllocation,
  StatusChangePreparation,
  StatusChangeExecutionValues,
  StatusChangeExecutionErrors,
} from "../../model/status-change-posting.types";
import { statusChangeBaseTotal } from "../../model/status-change-execution";
const props = defineProps<{
  values: StatusChangeExecutionValues;
  context: StatusChangePreparation | undefined;
  errors: StatusChangeExecutionErrors;
  disabled: boolean;
  uoms: readonly { code: string; dimension: string }[];
  uomError: string;
}>();
const emit = defineEmits<{
  change: [key: string, row: StatusChangeAllocation];
  select: [id: string, selected: boolean];
  split: [key: string];
  remove: [key: string];
  pick: [key: string];
  retryUnits: [];
}>();
const groups = computed(() => {
  const map = new Map<string, StatusChangeAllocation[]>();
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
  row: StatusChangeAllocation,
): readonly { code: string; dimension: string }[] {
  const dimension = props.uoms.find((v) => v.code === row.baseUom)?.dimension;
  return props.uoms.filter((v) => v.dimension === dimension);
}
</script>
<template>
  <div
    class="flex min-w-0 flex-col gap-4"
    aria-label="Распределения изменения состояния"
  >
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
      :aria-label="`Строка изменения состояния ${group.line.position + 1}: ${group.line.sku}`"
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
            statusChangeBaseTotal(group.rows) !== null
              ? `В этом изменении: ${statusChangeBaseTotal(group.rows)} ${group.line.baseUom}.`
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
          <div class="mt-3 min-w-0 rounded-md bg-muted p-3">
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
        Строка исключена из этого изменения состояния. Ввод сохранён.
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
