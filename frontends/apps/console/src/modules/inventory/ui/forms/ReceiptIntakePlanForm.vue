<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type {
  IntakeRow,
  ReceiptReferenceKind,
  ReceiptIntakeGroup,
  ReceiptIntakeErrors,
} from "../../model/receipt-posting.types";
import { hasRemaining, intakeBaseTotal } from "../../model/receipt-intake";
import ReceiptIntakeLinesForm from "./ReceiptIntakeLinesForm.vue";
defineProps<{
  groups: readonly ReceiptIntakeGroup[];
  disabled: boolean;
  errors: ReceiptIntakeErrors;
  uoms: readonly { code: string; dimension: string }[];
  rowCount: number;
  uomError: string;
  uomPending: boolean;
}>();
const emit = defineEmits<{
  retryUnits: [];
  select: [id: string, selected: boolean];
  fill: [id: string];
  change: [key: string, row: IntakeRow];
  remove: [key: string];
  split: [key: string];
  pick: [key: string, kind: ReceiptReferenceKind];
}>();
</script>
<template>
  <div
    class="flex min-w-0 flex-col gap-4"
    aria-label="Строки плана для приёмки"
  >
    <p v-if="uomError" role="alert" class="text-sm text-destructive">
      {{ uomError
      }}<Button
        type="button"
        variant="outline"
        :disabled="uomPending"
        @click="emit('retryUnits')"
        >Повторить загрузку единиц</Button
      >
    </p>
    <p v-if="errors.form" role="alert" class="text-sm text-destructive">
      {{ errors.form }}
    </p>
    <section
      v-for="group in groups"
      :key="group.line.documentLineId"
      :aria-label="`Строка плана ${group.line.position + 1}: ${group.line.sku}`"
      class="min-w-0 rounded-lg border p-3 sm:p-4"
    >
      <header class="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <h2 class="break-words font-medium">
            Строка {{ group.line.position + 1 }} · {{ group.line.sku }}
          </h2>
          <dl
            class="mt-2 grid grid-cols-3 gap-3 text-sm"
            aria-label="Прогресс строки"
          >
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
            role="status"
          >
            На сервере: выполнено {{ group.current.executedQuantity }}, осталось
            {{ group.current.remainingQuantity }} {{ group.current.baseUom }}.
            Примите новую версию для продолжения.
          </p>
        </div>
        <label class="flex items-center gap-2 text-sm"
          ><input
            type="checkbox"
            :checked="group.rows.some((row) => row.selected)"
            :disabled="disabled || !hasRemaining(group.line)"
            @change="
              emit(
                'select',
                group.line.documentLineId,
                ($event.target as HTMLInputElement).checked,
              )
            "
          />Принимать строку {{ group.line.position + 1 }}</label
        >
      </header>
      <template v-if="group.rows.some((row) => row.selected)">
        <div class="mb-3 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled"
            @click="emit('fill', group.line.documentLineId)"
            >Заполнить остаток строки</Button
          >
          <p class="text-xs text-muted-foreground">
            <template v-if="intakeBaseTotal(group.rows) !== null"
              >В этой приёмке: {{ intakeBaseTotal(group.rows) }}
              {{ group.line.baseUom }}.</template
            >
            <template v-else
              >Пересчёт введённых единиц и проверку общего количества выполнит
              сервер.</template
            >
          </p>
        </div>
        <ReceiptIntakeLinesForm
          :rows="group.rows"
          :disabled="disabled"
          :errors="errors"
          :uoms="uoms"
          :row-count="rowCount"
          @change="(key, row) => emit('change', key, row)"
          @remove="emit('remove', $event)"
          @split="emit('split', $event)"
          @pick="(key, kind) => emit('pick', key, kind)"
        />
      </template>
      <p v-else class="text-sm text-muted-foreground">
        {{
          hasRemaining(group.line)
            ? "Строка исключена из этой приёмки. Введённые распределения сохранены."
            : "Строка полностью выполнена."
        }}
      </p>
      <p
        v-if="errors.lines?.[group.line.documentLineId]"
        role="alert"
        class="mt-3 text-sm text-destructive"
      >
        {{ errors.lines[group.line.documentLineId] }}
      </p>
    </section>
  </div>
</template>
