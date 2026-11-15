<script setup lang="ts">
import type { ReturnOriginLine } from "../../model/return-origin.types";
import type { ReturnDraftLine, ReturnErrors } from "../../model/return.types";
import { Input } from "@/components/ui/input";
const props = defineProps<{
  origins: readonly ReturnOriginLine[];
  lines: readonly ReturnDraftLine[];
  errors: ReturnErrors;
  disabled: boolean;
  uoms: readonly { code: string; dimension: string }[];
}>();
const emit = defineEmits<{
  select: [origin: ReturnOriginLine, selected: boolean];
  change: [key: string, value: ReturnDraftLine];
}>();
function selected(id: string): ReturnDraftLine | undefined {
  return props.lines.find((v) => v.originExecutionLineId === id);
}
function quantity(id: string, value: string): void {
  const line = selected(id);
  if (line) emit("change", line.key, { ...line, quantity: value });
}
function unit(id: string, value: string): void {
  const line = selected(id);
  if (line) emit("change", line.key, { ...line, uom: value });
}
</script>
<template>
  <section class="space-y-3" aria-label="Строки основания возврата">
    <h2 class="text-lg font-semibold">Строки исходного исполнения</h2>
    <p class="text-sm text-muted-foreground">
      К возврату по основанию — количество ещё не возвращённого исходного факта.
      Подтверждение плана не резервирует его.
    </p>
    <p v-if="errors.lines" role="alert" class="text-sm text-destructive">
      {{ errors.lines }}
    </p>
    <section
      v-for="origin in origins"
      :key="origin.id"
      class="rounded-lg border p-3"
      :aria-label="`Исходная строка ${origin.position + 1}: ${origin.sku}`"
    >
      <label class="flex items-center gap-2 text-sm font-medium"
        ><input
          type="checkbox"
          :checked="!!selected(origin.id)"
          :disabled="
            disabled ||
            (!selected(origin.id) &&
              (!/[1-9]/.test(origin.remainingQuantity.split(/[eE]/)[0] ?? '') ||
                lines.length >= 100))
          "
          @change="
            emit('select', origin, ($event.target as HTMLInputElement).checked)
          "
        />{{ origin.sku }} · строка {{ origin.position + 1 }}</label
      >
      <p v-if="origin.lotNumber || origin.serialNumber" class="mt-2 text-sm">
        {{ origin.lotNumber ? `Партия ${origin.lotNumber}` : "" }}
        {{ origin.serialNumber ? `Серия ${origin.serialNumber}` : "" }}
      </p>
      <dl class="mt-3 grid gap-2 text-sm sm:grid-cols-3">
        <div>
          <dt class="text-muted-foreground">Исходно</dt>
          <dd>{{ origin.quantity }} {{ origin.baseUom }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Возвращено</dt>
          <dd>{{ origin.returnedQuantity }} {{ origin.baseUom }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">К возврату</dt>
          <dd>{{ origin.remainingQuantity }} {{ origin.baseUom }}</dd>
        </div>
      </dl>
      <div v-if="selected(origin.id)" class="mt-3 grid gap-3 sm:grid-cols-2">
        <label class="text-sm"
          >Количество<Input
            type="text"
            inputmode="decimal"
            :model-value="selected(origin.id)?.quantity"
            :disabled="disabled"
            @update:model-value="quantity(origin.id, String($event))"
        /></label>
        <label class="text-sm"
          >Единица<select
            class="mt-2 h-10 w-full rounded-md border bg-background px-3"
            :value="selected(origin.id)?.uom"
            :disabled="disabled"
            @change="
              unit(origin.id, ($event.target as HTMLSelectElement).value)
            "
          >
            <option
              v-for="u in uoms.filter(
                (u) =>
                  u.dimension ===
                  uoms.find((v) => v.code === origin.baseUom)?.dimension,
              )"
              :key="u.code"
              :value="u.code"
            >
              {{ u.code }}
            </option>
          </select></label
        >
        <p
          v-if="errors.lineFields[selected(origin.id)?.key ?? '']"
          role="alert"
          class="text-sm text-destructive sm:col-span-2"
        >
          {{
            Object.values(
              errors.lineFields[selected(origin.id)?.key ?? ""] ?? {},
            ).join(" ")
          }}
        </p>
      </div>
    </section>
  </section>
</template>
