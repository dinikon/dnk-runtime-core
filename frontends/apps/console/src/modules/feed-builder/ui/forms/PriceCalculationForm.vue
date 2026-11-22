<script setup lang="ts">
import { ref } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  FieldSet,
  FieldLegend,
  FieldGroup,
  Field,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import CalculationNodeEditor from "./CalculationNodeEditor.vue";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import {
  newNode,
  moveRule,
  quickExpression,
} from "../../model/feed-calculation.draft";
import type {
  SchemaCalculation,
  SchemaIssue,
} from "../../model/feed-schema.types";
import type { CalculationMetadata } from "../../model/feed-calculation.types";
const props = defineProps<{
  value: SchemaCalculation;
  metadata: CalculationMetadata;
  issues: SchemaIssue[];
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [value: SchemaCalculation] }>();
const base = ref("price.regular"),
  operation = ref<"percent" | "amount">("percent"),
  amount = ref("15");
function change(update: (value: SchemaCalculation) => void): void {
  if (props.disabled) return;
  const value = cloneSchemaValue(props.value);
  update(value);
  emit("change", value);
}
function add(): void {
  if (props.value.rules.length >= props.metadata.maxRules) return;
  change((v) => {
    v.rules.push({
      id: crypto.randomUUID(),
      condition: newNode("presence"),
      expression: { kind: "parameter", parameter: "price.sale" },
    });
  });
}
function move(index: number, delta: number): void {
  if (!props.disabled) emit("change", moveRule(props.value, index, delta));
}
function duplicate(index: number): void {
  if (props.value.rules.length >= props.metadata.maxRules) return;
  change((v) => {
    v.rules.splice(index + 1, 0, {
      ...cloneSchemaValue(v.rules[index]!),
      id: crypto.randomUUID(),
    });
  });
}
</script>
<template>
  <FieldSet :disabled="disabled"
    ><FieldLegend>Формула цены</FieldLegend
    ><FieldDescription
      >Проверяем IF сверху вниз. Выполняется первое совпадение; иначе — ELSE.
      Валюта служит меткой, пересчёт задаётся формулой.</FieldDescription
    ><FieldGroup>
      <div
        v-for="(rule, index) in value.rules"
        :key="rule.id"
        class="flex min-w-0 flex-col gap-3 rounded-lg border p-3"
        :aria-label="`Правило ${index + 1}`"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <strong
            >{{ index === 0 ? "IF" : "ELSE IF" }} · {{ index + 1 }}</strong
          >
          <div class="flex flex-wrap gap-1">
            <Button
              type="button"
              variant="outline"
              :disabled="disabled || index === 0"
              :aria-label="`Поднять правило ${index + 1}`"
              @click="move(index, -1)"
              >↑</Button
            ><Button
              type="button"
              variant="outline"
              :disabled="disabled || index === value.rules.length - 1"
              :aria-label="`Опустить правило ${index + 1}`"
              @click="move(index, 1)"
              >↓</Button
            ><Button
              type="button"
              variant="outline"
              :disabled="disabled || value.rules.length >= metadata.maxRules"
              @click="duplicate(index)"
              >Копировать</Button
            ><Button
              type="button"
              variant="outline"
              :disabled="disabled"
              @click="
                change((v) => {
                  v.rules.splice(index, 1);
                })
              "
              >Удалить</Button
            >
          </div>
        </div>
        <CalculationNodeEditor
          :node="rule.condition"
          category="condition"
          :metadata="metadata"
          :disabled="disabled"
          :path="['rules', index, 'condition']"
          :issues="issues"
          @change="
            change((v) => {
              v.rules[index]!.condition = $event;
            })
          "
        />
        <Field
          ><FieldLabel>THEN — цена</FieldLabel
          ><CalculationNodeEditor
            :node="rule.expression"
            category="number"
            :metadata="metadata"
            :disabled="disabled"
            :path="['rules', index, 'expression']"
            :issues="issues"
            @change="
              change((v) => {
                v.rules[index]!.expression = $event;
              })
            "
        /></Field>
      </div>
      <Button
        type="button"
        variant="outline"
        :disabled="disabled || value.rules.length >= metadata.maxRules"
        @click="add"
        >Добавить IF</Button
      >
      <Field
        ><FieldLabel>ELSE — цена по умолчанию</FieldLabel
        ><CalculationNodeEditor
          :node="value.defaultExpression"
          category="number"
          :metadata="metadata"
          :disabled="disabled"
          :path="['default_expression']"
          :issues="issues"
          @change="
            change((v) => {
              v.defaultExpression = $event;
            })
          "
      /></Field>
      <div class="flex flex-col gap-3 rounded-md bg-muted p-3">
        <strong class="text-sm">Быстрая формула для ELSE</strong>
        <Select v-model="base" :disabled="disabled"
          ><SelectTrigger aria-label="База наценки"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="p in metadata.parameters.filter(
                  (p) => p.valueType === 'number',
                )"
                :key="p.id"
                :value="p.id"
                >{{ p.label }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        >
        <Select v-model="operation" :disabled="disabled"
          ><SelectTrigger aria-label="Способ наценки"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem value="percent">Прибавить процент</SelectItem
              ><SelectItem value="amount"
                >Прибавить сумму</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        >
        <Input
          v-model="amount"
          :disabled="disabled"
          aria-label="Размер наценки"
          inputmode="decimal"
        /><Button
          type="button"
          variant="outline"
          :disabled="disabled || !amount.trim()"
          @click="
            change((v) => {
              v.defaultExpression = quickExpression(base, operation, amount);
            })
          "
          >Применить к ELSE</Button
        >
      </div>
    </FieldGroup></FieldSet
  >
</template>
