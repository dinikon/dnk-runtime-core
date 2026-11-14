<script setup lang="ts">
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type {
  SourceValues,
  SourceFieldErrors,
  FulfillmentMode,
} from "../../model/supplier-source.types";
import { fulfillmentLabels } from "../../model/supplier-source.constants";
const props = defineProps<{
  values: SourceValues;
  errors: SourceFieldErrors;
  disabled: boolean;
  editing: boolean;
}>();
const emit = defineEmits<{ change: [values: SourceValues] }>();
function text(
  field: "name" | "externalWarehouseCode" | "leadTimeSeconds" | "ttlSeconds",
  value: string | number,
): void {
  emit("change", { ...props.values, [field]: String(value) });
}
function mode(
  value: FulfillmentMode,
  checked: boolean | "indeterminate",
): void {
  const modes = props.values.fulfillmentModes.filter((item) => item !== value);
  if (checked === true) modes.push(value);
  emit("change", { ...props.values, fulfillmentModes: modes });
}
</script>
<template>
  <FieldGroup class="min-w-0 [&_[data-slot=native-select-wrapper]]:w-full">
    <Field :data-invalid="!!errors.name"
      ><FieldLabel for="source-name">Название источника</FieldLabel
      ><Input
        id="source-name"
        :model-value="values.name"
        :disabled="disabled"
        :aria-invalid="!!errors.name"
        aria-describedby="source-name-error"
        @update:model-value="text('name', $event)" /><FieldError
        v-if="errors.name"
        id="source-name-error"
        :errors="[errors.name]"
    /></Field>
    <Field :data-invalid="!!errors.externalWarehouseCode"
      ><FieldLabel for="source-external-code">Внешний код</FieldLabel
      ><Input
        id="source-external-code"
        :model-value="values.externalWarehouseCode"
        :disabled="disabled"
        :aria-invalid="!!errors.externalWarehouseCode"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
        @update:model-value="
          text('externalWarehouseCode', $event)
        " /><FieldDescription
        >Код склада или канала у поставщика. Регистр и ведущие нули сохраняются;
        пустое поле убирает код.</FieldDescription
      ><FieldError
        v-if="errors.externalWarehouseCode"
        :errors="[errors.externalWarehouseCode]"
    /></Field>
    <fieldset :disabled="disabled" class="flex flex-col gap-3">
      <legend class="mb-3 text-sm font-medium">Режимы исполнения</legend>
      <label
        v-for="(label, key) in fulfillmentLabels"
        :key="key"
        class="flex items-center gap-2 text-sm"
        ><Checkbox
          :model-value="values.fulfillmentModes.includes(key)"
          :aria-label="label"
          @update:model-value="mode(key, $event)"
        />{{ label }}</label
      ><FieldError
        v-if="errors.fulfillmentModes"
        :errors="[errors.fulfillmentModes]"
      />
    </fieldset>
    <Field :data-invalid="!!errors.leadTimeSeconds"
      ><FieldLabel for="source-lead-time">Срок поставки, секунды</FieldLabel
      ><Input
        id="source-lead-time"
        :model-value="values.leadTimeSeconds"
        inputmode="numeric"
        :disabled="disabled"
        :aria-invalid="!!errors.leadTimeSeconds"
        @update:model-value="
          text('leadTimeSeconds', $event)
        " /><FieldDescription
        >0 — немедленная поставка. 3 600 секунд = 1 час; 86 400 = 1
        день.</FieldDescription
      ><FieldError
        v-if="errors.leadTimeSeconds"
        :errors="[errors.leadTimeSeconds]"
    /></Field>
    <div class="border-t pt-5">
      <h3 class="font-medium">Актуальность внешнего наличия</h3>
      <p class="mt-1 text-sm text-muted-foreground">
        Настройки обработки данных поставщика при последующих загрузках и оценке
        наличия.
      </p>
    </div>
    <Field :data-invalid="!!errors.ttlSeconds"
      ><FieldLabel for="source-ttl">TTL, секунды</FieldLabel
      ><Input
        id="source-ttl"
        :model-value="values.ttlSeconds"
        inputmode="numeric"
        :disabled="disabled"
        :aria-invalid="!!errors.ttlSeconds"
        @update:model-value="text('ttlSeconds', $event)" /><FieldDescription
        >Положительное время актуальности наблюдения с момента получения. 900
        секунд = 15 минут; 3 600 = 1 час.</FieldDescription
      ><FieldError v-if="errors.ttlSeconds" :errors="[errors.ttlSeconds]"
    /></Field>
    <Field
      ><FieldLabel for="source-stale">Устаревшие данные</FieldLabel
      ><NativeSelect
        id="source-stale"
        :model-value="values.staleBehavior"
        :disabled="disabled"
        @update:model-value="
          emit('change', {
            ...values,
            staleBehavior:
              $event === 'BLOCK_AUTOMATIC_SALE'
                ? 'BLOCK_AUTOMATIC_SALE'
                : 'MARK_UNKNOWN',
          })
        "
        ><NativeSelectOption value="MARK_UNKNOWN"
          >Считать наличие неизвестным</NativeSelectOption
        ><NativeSelectOption value="BLOCK_AUTOMATIC_SALE"
          >Неизвестное наличие и запрет автоматической
          продажи</NativeSelectOption
        ></NativeSelect
      ><FieldError v-if="errors.staleBehavior" :errors="[errors.staleBehavior]"
    /></Field>
    <Field
      ><FieldLabel for="source-missing"
        >SKU отсутствует в полном снимке</FieldLabel
      ><NativeSelect
        id="source-missing"
        :model-value="values.missingSkuBehavior"
        :disabled="disabled"
        @update:model-value="
          emit('change', {
            ...values,
            missingSkuBehavior:
              $event === 'KEEP_LAST' ? 'KEEP_LAST' : 'MARK_UNKNOWN',
          })
        "
        ><NativeSelectOption value="MARK_UNKNOWN"
          >Считать наличие неизвестным</NativeSelectOption
        ><NativeSelectOption value="KEEP_LAST"
          >Сохранить последнее наблюдение</NativeSelectOption
        ></NativeSelect
      ><FieldDescription
        >Применяется только к успешному полному снимку. Ошибка загрузки или
        частичный ответ не означают отсутствие SKU. Последнее наблюдение
        продолжает устаревать по TTL.</FieldDescription
      ><FieldError
        v-if="errors.missingSkuBehavior"
        :errors="[errors.missingSkuBehavior]"
    /></Field>
    <Field v-if="editing" orientation="horizontal"
      ><FieldLabel for="source-active">Источник активен</FieldLabel
      ><Switch
        id="source-active"
        :model-value="values.isActive"
        :disabled="disabled"
        @update:model-value="emit('change', { ...values, isActive: $event })"
    /></Field>
    <p v-if="editing" class="text-sm text-muted-foreground">
      Деактивация запрещает выбор источника для исполнения. Изменение TTL не
      пересчитывает сроки уже сохранённых наблюдений.
    </p>
  </FieldGroup>
</template>
