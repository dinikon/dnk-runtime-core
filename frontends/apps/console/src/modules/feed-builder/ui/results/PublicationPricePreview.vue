<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { Field, FieldLabel } from "@/components/ui/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { CalculationPreview } from "../../model/feed-calculation.types";
const props = defineProps<{
  fields: { id: string; label: string; manual: boolean }[];
  fieldId: string;
  result: CalculationPreview | null;
  stale: boolean;
  pending: boolean;
  error: string;
  disabled: boolean;
  manual: boolean;
}>();
const branch = computed(() => {
  const value = props.result;
  if (!value) return "";
  if (!value.selectedRuleId)
    return value.usedDefault
      ? "ELSE"
      : value.validationStatus === "INVALID"
        ? "Расчёт не завершён"
        : "Источник";
  const index = value.steps.find(
    (step) => step.ruleId === value.selectedRuleId && step.path[0] === "rules",
  )?.path[1];
  return typeof index === "number" ? `IF · ${index + 1}` : "IF";
});
const emit = defineEmits<{ field: [id: string]; preview: [] }>();
</script>
<template>
  <section
    class="flex min-w-0 flex-col gap-3 rounded border p-4"
    aria-label="Проверка цены публикации"
  >
    <h3 class="font-medium">Проверка цены</h3>
    <p class="text-sm text-muted-foreground">
      Расчёт использует сохранённую схему фида и выбранную позицию.
    </p>
    <Field
      ><FieldLabel for="publication-price-field">Денежное поле схемы</FieldLabel
      ><Select
        :model-value="fieldId"
        @update:model-value="emit('field', String($event))"
        ><SelectTrigger id="publication-price-field"
          ><SelectValue placeholder="Выберите поле" /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem v-for="f in fields" :key="f.id" :value="f.id"
              >{{ f.label }}{{ f.manual ? " · Вручную" : "" }}</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    >
    <p v-if="!fields.length" class="text-sm text-muted-foreground">
      Добавьте денежное поле на вкладке «Схема».
    </p>
    <p v-if="manual" class="text-sm text-muted-foreground">
      Этому полю требуется ручное значение. Редактор значений публикации будет
      добавлен следующим срезом.
    </p>
    <Button
      type="button"
      :disabled="disabled || manual || !fieldId"
      @click="emit('preview')"
      >{{ pending ? "Рассчитываем…" : "Рассчитать цену позиции" }}</Button
    ><Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    ><Alert v-if="stale"
      ><AlertDescription
        >Предыдущий результат устарел. Повторите расчёт.</AlertDescription
      ></Alert
    >
    <div
      v-if="result"
      class="flex min-w-0 flex-col gap-2"
      :class="stale ? 'opacity-60' : ''"
    >
      <p
        v-if="result.resolvedValue"
        class="break-all rounded bg-muted p-3 text-xl font-semibold"
        data-testid="publication-price"
      >
        {{ result.resolvedValue.amount
        }}<span v-if="result.resolvedValue.currency" class="ml-1">{{
          result.resolvedValue.currency
        }}</span>
      </p>
      <p class="text-sm">Ветка: {{ branch }}</p>
      <Alert
        v-for="(issue, index) in result.issues"
        :key="index"
        variant="destructive"
        ><AlertDescription
          >{{ issue.message
          }}<span class="block break-all text-xs">{{
            issue.path.join(" → ")
          }}</span></AlertDescription
        ></Alert
      >
      <details>
        <summary class="cursor-pointer text-sm">
          Параметры и шаги расчёта
        </summary>
        <dl class="mt-2 grid grid-cols-2 gap-2 text-sm">
          <template v-for="p in result.parameters" :key="p.id"
            ><dt class="break-all">{{ p.id }}</dt>
            <dd class="break-all">
              {{ p.value === null ? "Отсутствует" : String(p.value) }}
            </dd></template
          >
        </dl>
        <ol class="mt-2 flex flex-col gap-2 text-sm">
          <li
            v-for="(step, index) in result.steps"
            :key="index"
            class="break-all"
          >
            {{ step.operation }} → {{ String(step.value)
            }}<span class="block text-xs text-muted-foreground">{{
              step.path.join(" → ")
            }}</span>
          </li>
        </ol>
      </details>
      <p class="break-all text-xs text-muted-foreground">
        Снимок {{ result.asOf }} · версия Feed {{ result.version }}
      </p>
    </div>
  </section>
</template>
