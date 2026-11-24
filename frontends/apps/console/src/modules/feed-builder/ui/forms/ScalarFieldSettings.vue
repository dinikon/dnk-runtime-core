<script setup lang="ts">
import { computed } from "vue";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Field, FieldError, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { CalculationMetadata } from "../../model/feed-calculation.types";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import type { ScalarTypeDraft, SchemaIssue, SchemaMetadata, SchemaNode } from "../../model/feed-schema.types";
import CalculationNodeEditor from "./CalculationNodeEditor.vue";

const props = defineProps<{
  value: ScalarTypeDraft;
  metadata: SchemaMetadata;
  issues: SchemaIssue[];
  disabled: boolean;
  calculationMetadata?: CalculationMetadata;
}>();
const emit = defineEmits<{ change: [value: ScalarTypeDraft] }>();
const sources = computed(() => props.metadata.sources.filter((source) => source.fieldKinds.includes(props.value.kind)));
const modes = computed(() => props.metadata.fieldTypes.find((type) => type.kind === props.value.kind)?.editableModes ?? []);
const labels: Record<string, string> = {
  SOURCE: "Источник",
  MANUAL: "Вручную в публикации",
  CONSTANT: "Заданное значение",
  CALCULATED: "Вычислить",
};
function change(update: (draft: ScalarTypeDraft) => void): void {
  if (props.disabled) return;
  const draft = cloneSchemaValue(props.value);
  update(draft);
  emit("change", draft);
}
function modeChanged(mode: string): void {
  change((draft) => {
    if (mode === "SOURCE") {
      const source = sources.value[0];
      if (source) draft.value = { kind: "SOURCE", source: { provider: source.provider, path: source.path } };
    } else if (mode === "MANUAL") draft.value = { kind: "MANUAL" };
    else if (mode === "CONSTANT") {
      if (draft.kind === "integer") draft.value = { kind: "CONSTANT", value: "0" };
      else draft.value = { kind: "CONSTANT", value: false };
    } else if (mode === "CALCULATED" && draft.kind === "boolean" && props.calculationMetadata) {
      draft.value = {
        kind: "CALCULATED",
        condition: {
          kind: "comparison", operator: "EQ",
          left: { kind: "parameter", parameter: "stock.in_stock" },
          right: { kind: "scalar", valueType: "boolean", value: true },
        },
        thenValue: true,
        elseValue: false,
      };
    }
  });
}
function setCondition(condition: SchemaNode): void {
  change((draft) => {
    if (draft.kind === "boolean" && draft.value.kind === "CALCULATED")
      draft.value.condition = condition;
  });
}
function setBranch(key: "thenValue" | "elseValue", value: boolean): void {
  change((draft) => {
    if (draft.kind === "boolean" && draft.value.kind === "CALCULATED")
      draft.value[key] = value;
  });
}
</script>

<template>
  <FieldSet :disabled="disabled">
    <FieldLegend>Получение значения</FieldLegend>
    <FieldGroup>
      <Field>
        <FieldLabel for="scalar-field-mode">Способ заполнения</FieldLabel>
        <Select :model-value="value.value.kind" :disabled="disabled" @update:model-value="modeChanged(String($event))">
          <SelectTrigger id="scalar-field-mode"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem v-for="mode in modes" :key="mode" :value="mode" :disabled="mode === 'CALCULATED' && !calculationMetadata">
              {{ labels[mode] }}
            </SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field v-if="value.value.kind === 'SOURCE'">
        <FieldLabel for="scalar-field-source">Источник Catalog</FieldLabel>
        <Select :model-value="value.value.source.path" :disabled="disabled" @update:model-value="change((draft) => {
          const source = sources.find((entry) => entry.path === $event);
          if (source) draft.value = { kind: 'SOURCE', source: { provider: source.provider, path: source.path } };
        })">
          <SelectTrigger id="scalar-field-source"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem v-for="source in sources" :key="source.path" :value="source.path">{{ source.label }}</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field v-if="value.kind === 'integer' && value.value.kind === 'CONSTANT'">
        <FieldLabel for="scalar-integer-value">Целое число</FieldLabel>
        <Input id="scalar-integer-value" inputmode="numeric" :model-value="value.value.value"
          @update:model-value="change((draft) => {
            if (draft.kind === 'integer' && draft.value.kind === 'CONSTANT') draft.value.value = String($event);
          })" />
      </Field>
      <Field v-if="value.kind === 'boolean' && value.value.kind === 'CONSTANT'">
        <FieldLabel for="scalar-boolean-value">Заданное значение</FieldLabel>
        <Select :model-value="String(value.value.value)" :disabled="disabled" @update:model-value="change((draft) => {
          if (draft.kind === 'boolean' && draft.value.kind === 'CONSTANT') draft.value.value = $event === 'true';
        })">
          <SelectTrigger id="scalar-boolean-value"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="true">true</SelectItem><SelectItem value="false">false</SelectItem></SelectContent>
        </Select>
      </Field>
      <template v-if="value.kind === 'boolean' && value.value.kind === 'CALCULATED' && calculationMetadata">
        <Field>
          <FieldLabel>Условие IF</FieldLabel>
          <CalculationNodeEditor
            :node="value.value.condition"
            :metadata="calculationMetadata"
            :issues="issues"
            :path="['condition']"
            :disabled="disabled"
            category="condition"
            @change="setCondition"
          />
        </Field>
        <div class="grid gap-3 sm:grid-cols-2">
          <Field v-for="branch in (['thenValue', 'elseValue'] as const)" :key="branch">
            <FieldLabel :for="'scalar-' + branch">{{ branch === "thenValue" ? "THEN" : "ELSE" }}</FieldLabel>
            <Select :model-value="String(value.value[branch])" :disabled="disabled"
              @update:model-value="setBranch(branch, $event === 'true')">
              <SelectTrigger :id="'scalar-' + branch"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="true">true</SelectItem><SelectItem value="false">false</SelectItem></SelectContent>
            </Select>
          </Field>
        </div>
      </template>
      <Field orientation="horizontal">
        <Checkbox id="scalar-required" :model-value="value.constraints.required" :disabled="disabled"
          @update:model-value="change((draft) => { draft.constraints.required = $event === true; })" />
        <FieldLabel for="scalar-required">Значение обязательно</FieldLabel>
      </Field>
      <div v-if="value.kind === 'integer'" class="grid gap-3 sm:grid-cols-2">
        <Field v-for="key in (['minValue', 'maxValue'] as const)" :key="key">
          <FieldLabel :for="'scalar-' + key">{{ key === "minValue" ? "Минимум" : "Максимум" }}</FieldLabel>
          <Input :id="'scalar-' + key" inputmode="numeric" :model-value="value.constraints[key]"
            @update:model-value="change((draft) => {
              if (draft.kind === 'integer') draft.constraints[key] = String($event);
            })" />
        </Field>
      </div>
      <FieldError v-for="(issue, index) in issues.filter((issue) =>
        issue.path.includes('constraints') || (issue.path.includes('value') && !issue.path.includes('condition'))
      )" :key="index">{{ issue.message }}</FieldError>
    </FieldGroup>
  </FieldSet>
</template>
