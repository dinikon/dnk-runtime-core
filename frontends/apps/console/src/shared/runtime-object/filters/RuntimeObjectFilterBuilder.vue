<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Plus, Trash2 } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  RuntimeFieldDescription,
  RuntimeFilter,
  RuntimeFilterCondition,
} from "@/shared/runtime-object";
import RuntimeMultiSelect from "@/shared/runtime-object/form/RuntimeMultiSelect.vue";

interface FilterConditionDraft {
  id: string;
  field: string;
  op: string;
  value: string | string[];
  secondValue: string;
}

const props = defineProps<{
  fields: RuntimeFieldDescription[];
  modelValue: RuntimeFilter | null;
}>();

const emit = defineEmits<{
  (event: "apply", filter: RuntimeFilter | null): void;
  (event: "cancel"): void;
}>();

const noValueOperators = new Set([
  "is_null",
  "is_not_null",
  "is_empty",
  "is_not_empty",
]);
const listOperators = new Set([
  "in",
  "contains_any",
  "contains_all",
  "not_contains_any",
]);

const logic = ref<"and" | "or">("and");
const conditions = ref<FilterConditionDraft[]>([]);
let nextConditionId = 1;

const filterableFields = computed(() =>
  props.fields.filter((field) => field.filter.enabled),
);

watch(
  () => props.modelValue,
  (filter) => {
    hydrate(filter);
  },
  { immediate: true },
);

function hydrate(filter: RuntimeFilter | null) {
  conditions.value = [];
  logic.value = "and";

  if (!filter) {
    addCondition();
    return;
  }

  if ("and" in filter || "or" in filter) {
    const groupLogic = "and" in filter ? "and" : "or";
    logic.value = groupLogic;
    const groupItems = "and" in filter ? filter.and : filter.or;
    conditions.value = groupItems
      .filter(isCondition)
      .map((condition) => conditionToDraft(condition));
  } else {
    conditions.value = [conditionToDraft(filter)];
  }

  if (conditions.value.length === 0) {
    addCondition();
  }
}

function isCondition(filter: RuntimeFilter): filter is RuntimeFilterCondition {
  return "field" in filter && "op" in filter;
}

function conditionToDraft(
  condition: RuntimeFilterCondition,
): FilterConditionDraft {
  const value = condition.value;
  return {
    id: createConditionId(),
    field: condition.field,
    op: condition.op,
    value: Array.isArray(value)
      ? value.map((item) => String(item))
      : value === null || value === undefined
        ? ""
        : String(value),
    secondValue:
      Array.isArray(value) && value.length > 1 ? String(value[1]) : "",
  };
}

function createConditionId(): string {
  const id = `condition-${nextConditionId}`;
  nextConditionId += 1;
  return id;
}

function addCondition() {
  const field = filterableFields.value[0];
  conditions.value.push({
    id: createConditionId(),
    field: field?.field_name ?? "",
    op: field?.filter.operators[0] ?? "",
    value: "",
    secondValue: "",
  });
}

function removeCondition(id: string) {
  conditions.value = conditions.value.filter(
    (condition) => condition.id !== id,
  );
  if (conditions.value.length === 0) {
    addCondition();
  }
}

function fieldFor(condition: FilterConditionDraft) {
  return filterableFields.value.find(
    (field) => field.field_name === condition.field,
  );
}

function operatorsFor(condition: FilterConditionDraft): string[] {
  return fieldFor(condition)?.filter.operators ?? [];
}

function optionsFor(condition: FilterConditionDraft) {
  const field = fieldFor(condition);
  return field?.filter.options.length
    ? field.filter.options
    : (field?.options ?? []);
}

function setConditionField(
  condition: FilterConditionDraft,
  fieldName: unknown,
) {
  const field = filterableFields.value.find(
    (item) => item.field_name === String(fieldName),
  );

  condition.field = field?.field_name ?? "";
  condition.op = field?.filter.operators[0] ?? "";
  condition.value = "";
  condition.secondValue = "";
}

function setConditionOperator(
  condition: FilterConditionDraft,
  operator: unknown,
) {
  condition.op = String(operator);
  condition.value = "";
  condition.secondValue = "";
}

function shouldUseMultiSelect(condition: FilterConditionDraft): boolean {
  const field = fieldFor(condition);
  return (
    listOperators.has(condition.op) ||
    field?.filter.input === "multiselect" ||
    field?.type === "multiselect"
  );
}

function shouldUseSingleSelect(condition: FilterConditionDraft): boolean {
  const field = fieldFor(condition);
  return (
    !shouldUseMultiSelect(condition) &&
    (field?.filter.input === "select" || field?.type === "select")
  );
}

function valueAsString(condition: FilterConditionDraft): string {
  return typeof condition.value === "string" ? condition.value : "";
}

function valueAsArray(condition: FilterConditionDraft): string[] {
  return Array.isArray(condition.value) ? condition.value : [];
}

function setStringValue(condition: FilterConditionDraft, value: unknown) {
  condition.value = value === null || value === undefined ? "" : String(value);
}

function setArrayValue(condition: FilterConditionDraft, value: string[]) {
  condition.value = value;
}

function operatorLabel(operator: string): string {
  return operator.replaceAll("_", " ");
}

function applyFilter() {
  const normalizedConditions = conditions.value
    .map((condition) => normalizeCondition(condition))
    .filter(
      (condition): condition is RuntimeFilterCondition => condition !== null,
    );

  if (normalizedConditions.length === 0) {
    emit("apply", null);
    return;
  }

  if (normalizedConditions.length === 1) {
    emit("apply", normalizedConditions[0]);
    return;
  }

  emit(
    "apply",
    logic.value === "and"
      ? { and: normalizedConditions }
      : { or: normalizedConditions },
  );
}

function normalizeCondition(
  condition: FilterConditionDraft,
): RuntimeFilterCondition | null {
  const field = fieldFor(condition);
  if (!field || !condition.op) {
    return null;
  }

  if (noValueOperators.has(condition.op)) {
    return {
      field: field.field_name,
      op: condition.op,
      value: null,
    };
  }

  if (condition.op === "between") {
    if (!valueAsString(condition) || !condition.secondValue) {
      return null;
    }

    return {
      field: field.field_name,
      op: condition.op,
      value: [valueAsString(condition), condition.secondValue],
    };
  }

  if (listOperators.has(condition.op)) {
    const value = Array.isArray(condition.value)
      ? condition.value
      : valueAsString(condition)
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

    if (value.length === 0) {
      return null;
    }

    return {
      field: field.field_name,
      op: condition.op,
      value,
    };
  }

  const value = valueAsString(condition).trim();
  if (!value) {
    return null;
  }

  return {
    field: field.field_name,
    op: condition.op,
    value,
  };
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-1">
      <Field>
        <FieldLabel>Group logic</FieldLabel>
        <Select
          :model-value="logic"
          @update:model-value="logic = String($event) === 'or' ? 'or' : 'and'"
        >
          <SelectTrigger class="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="and">AND</SelectItem>
            <SelectItem value="or">OR</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <FieldGroup>
        <div
          v-for="condition in conditions"
          :key="condition.id"
          class="rounded-lg border p-3"
        >
          <div class="mb-3 flex items-center justify-between gap-2">
            <span class="text-sm font-medium">Condition</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              @click="removeCondition(condition.id)"
            >
              <Trash2 class="size-4" />
              <span class="sr-only">Remove condition</span>
            </Button>
          </div>

          <div class="grid gap-3">
            <Field>
              <FieldLabel>Field</FieldLabel>
              <Select
                :model-value="condition.field"
                @update:model-value="setConditionField(condition, $event)"
              >
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="Select field" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="field in filterableFields"
                    :key="field.field_name"
                    :value="field.field_name"
                  >
                    {{ field.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel>Operator</FieldLabel>
              <Select
                :model-value="condition.op"
                @update:model-value="setConditionOperator(condition, $event)"
              >
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="Select operator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="operator in operatorsFor(condition)"
                    :key="operator"
                    :value="operator"
                  >
                    {{ operatorLabel(operator) }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </Field>

            <p
              v-if="noValueOperators.has(condition.op)"
              class="text-sm text-muted-foreground"
            >
              This operator does not require a value.
            </p>

            <div v-else-if="condition.op === 'between'" class="grid gap-3">
              <Field>
                <FieldLabel>From</FieldLabel>
                <Input
                  :type="
                    fieldFor(condition)?.filter.input === 'datetime'
                      ? 'datetime-local'
                      : 'text'
                  "
                  :model-value="valueAsString(condition)"
                  @update:model-value="setStringValue(condition, $event)"
                />
              </Field>
              <Field>
                <FieldLabel>To</FieldLabel>
                <Input
                  :type="
                    fieldFor(condition)?.filter.input === 'datetime'
                      ? 'datetime-local'
                      : 'text'
                  "
                  :model-value="condition.secondValue"
                  @update:model-value="condition.secondValue = String($event)"
                />
              </Field>
            </div>

            <Field v-else>
              <FieldLabel>Value</FieldLabel>
              <RuntimeMultiSelect
                v-if="shouldUseMultiSelect(condition)"
                :model-value="valueAsArray(condition)"
                :options="optionsFor(condition)"
                placeholder="Select values"
                @update:model-value="setArrayValue(condition, $event)"
              />
              <Select
                v-else-if="shouldUseSingleSelect(condition)"
                :model-value="valueAsString(condition)"
                @update:model-value="setStringValue(condition, $event)"
              >
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="Select value" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="option in optionsFor(condition)"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <Input
                v-else
                :type="
                  fieldFor(condition)?.filter.input === 'datetime'
                    ? 'datetime-local'
                    : 'text'
                "
                :model-value="valueAsString(condition)"
                :placeholder="
                  listOperators.has(condition.op)
                    ? 'Comma separated values'
                    : undefined
                "
                @update:model-value="setStringValue(condition, $event)"
              />
            </Field>
          </div>
        </div>
      </FieldGroup>

      <Button
        type="button"
        variant="outline"
        class="w-full"
        @click="addCondition"
      >
        <Plus class="size-4" />
        Add condition
      </Button>
    </div>

    <div class="mt-6 flex justify-end gap-2 border-t pt-4">
      <Button type="button" variant="outline" @click="emit('cancel')">
        Cancel
      </Button>
      <Button type="button" @click="applyFilter">Apply filters</Button>
    </div>
  </div>
</template>
