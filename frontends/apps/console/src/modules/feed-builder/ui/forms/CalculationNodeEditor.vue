<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import { newNode } from "../../model/feed-calculation.draft";
import type { SchemaNode, SchemaIssue } from "../../model/feed-schema.types";
import type {
  CalculationMetadata,
  NodeCategory,
  NodeKind,
} from "../../model/feed-calculation.types";
const props = defineProps<{
  node: SchemaNode;
  category: NodeCategory;
  metadata: CalculationMetadata;
  disabled: boolean;
  depth?: number;
  path: (string | number)[];
  issues: SchemaIssue[];
}>();
const emit = defineEmits<{ change: [node: SchemaNode] }>();
const depth = computed(() => props.depth ?? 0);
const kinds = computed(() =>
  props.category === "condition"
    ? ["comparison", "presence", "logical"]
    : props.category === "number"
      ? ["parameter", "decimal", "arithmetic", "function"]
      : [
          "parameter",
          "decimal",
          "scalar",
          "collection",
          "arithmetic",
          "function",
        ],
);
const labels: Record<string, string> = {
  parameter: "Параметр товара",
  decimal: "Число",
  scalar: "Значение",
  collection: "Список значений",
  arithmetic: "Арифметика",
  function: "Функция",
  comparison: "Сравнение",
  presence: "Наличие значения",
  logical: "Группа условий",
};
const category = computed(() =>
  props.node.kind === "arithmetic"
    ? "arithmetic"
    : props.node.kind === "function"
      ? "function"
      : props.node.kind,
);
const operations = computed(() =>
  props.metadata.operations.filter((o) => o.category === category.value),
);
const parameters = computed(() =>
  props.metadata.parameters.filter(
    (p) => props.category !== "number" || p.valueType === "number",
  ),
);
const messages = computed(() =>
  props.issues.filter(
    (i) =>
      JSON.stringify(i.path.slice(-props.path.length)) ===
      JSON.stringify(props.path),
  ),
);
function change(update: (node: SchemaNode) => void): void {
  if (props.disabled) return;
  const node = cloneSchemaValue(props.node);
  update(node);
  emit("change", node);
}
function setKind(value: string): void {
  if (!props.disabled && kinds.value.includes(value))
    emit("change", newNode(value as NodeKind, props.category));
}
function setOperation(value: string): void {
  if (!operations.value.some((o) => o.code === value)) return;
  change((n) => {
    if (n.kind === "arithmetic") {
      n.operator = value as typeof n.operator;
      if (value === "NEGATE") {
        n.operand = n.operand ?? n.left ?? newNode("decimal");
        delete n.left;
        delete n.right;
      } else {
        n.left = n.left ?? n.operand ?? newNode("parameter");
        n.right = n.right ?? newNode("decimal");
        delete n.operand;
      }
    } else if (n.kind === "function") {
      n.function = value as typeof n.function;
      n.arguments =
        value === "ABS"
          ? [n.arguments[0] ?? newNode("decimal")]
          : [
              n.arguments[0] ?? newNode("parameter"),
              n.arguments[1] ?? newNode("decimal"),
              ...n.arguments.slice(2),
            ];
    } else if (n.kind === "comparison" || n.kind === "presence")
      n.operator = value as typeof n.operator;
    else if (n.kind === "logical") {
      n.operator = value as typeof n.operator;
      if (value === "NOT") n.operands = [n.operands[0] ?? newNode("presence")];
    }
  });
}
function setScalarType(value: string): void {
  if (!["string", "uuid", "boolean"].includes(value)) return;
  change((n) => {
    if (n.kind === "scalar") {
      n.valueType = value as typeof n.valueType;
      n.value = value === "boolean" ? false : "";
    }
    if (n.kind === "collection") {
      n.itemType = value as typeof n.itemType;
      n.items = [
        {
          kind: "scalar",
          valueType: n.itemType,
          value: value === "boolean" ? false : "",
        },
      ];
    }
  });
}
function child(key: "left" | "right" | "operand", value: SchemaNode): void {
  change((n) => {
    if (n.kind === "arithmetic") n[key] = value;
    else if (n.kind === "comparison" && key !== "operand") n[key] = value;
  });
}
function listChild(index: number, value: SchemaNode): void {
  change((n) => {
    if (n.kind === "function") n.arguments[index] = value;
    else if (n.kind === "logical") n.operands[index] = value;
  });
}
function listRemove(index: number): void {
  change((n) => {
    if (n.kind === "function" && n.arguments.length > 2)
      n.arguments.splice(index, 1);
    else if (n.kind === "logical" && n.operands.length > 1)
      n.operands.splice(index, 1);
  });
}
const nestedDisabled = computed(
  () => props.disabled || depth.value + 1 >= props.metadata.maxDepth,
);
</script>
<template>
  <div
    class="flex min-w-0 flex-col gap-3 rounded-md border p-3"
    :aria-label="labels[node.kind]"
  >
    <div class="flex flex-wrap gap-2">
      <Select
        :model-value="node.kind"
        :disabled="disabled"
        @update:model-value="setKind(String($event))"
        ><SelectTrigger class="w-full sm:w-48" aria-label="Тип узла"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem v-for="kind in kinds" :key="kind" :value="kind">{{
              labels[kind]
            }}</SelectItem></SelectGroup
          ></SelectContent
        ></Select
      >
      <Select
        v-if="operations.length"
        :model-value="
          node.kind === 'function'
            ? node.function
            : 'operator' in node
              ? node.operator
              : undefined
        "
        :disabled="disabled"
        @update:model-value="setOperation(String($event))"
        ><SelectTrigger class="w-full sm:w-48" aria-label="Операция"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem
              v-for="op in operations"
              :key="op.code"
              :value="op.code"
              >{{ op.label }}</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      >
    </div>
    <Select
      v-if="node.kind === 'parameter' || node.kind === 'presence'"
      :model-value="node.parameter"
      :disabled="disabled"
      @update:model-value="
        change((n) => {
          if (n.kind === 'parameter' || n.kind === 'presence')
            n.parameter = String($event);
        })
      "
      ><SelectTrigger aria-label="Параметр"><SelectValue /></SelectTrigger
      ><SelectContent
        ><SelectGroup
          ><SelectItem
            v-for="p in node.kind === 'presence'
              ? metadata.parameters
              : parameters"
            :key="p.id"
            :value="p.id"
            >{{ p.label }}</SelectItem
          ></SelectGroup
        ></SelectContent
      ></Select
    >
    <Input
      v-if="node.kind === 'decimal'"
      :model-value="node.value"
      :disabled="disabled"
      aria-label="Числовая константа"
      inputmode="decimal"
      @update:model-value="
        change((n) => {
          if (n.kind === 'decimal') n.value = String($event);
        })
      "
    />
    <template v-if="node.kind === 'scalar' || node.kind === 'collection'">
      <Select
        :model-value="node.kind === 'scalar' ? node.valueType : node.itemType"
        :disabled="disabled"
        @update:model-value="setScalarType(String($event))"
        ><SelectTrigger aria-label="Тип значения"><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem value="string">Текст</SelectItem
            ><SelectItem value="uuid">UUID товара</SelectItem
            ><SelectItem value="boolean">Да / Нет</SelectItem></SelectGroup
          ></SelectContent
        ></Select
      >
      <template v-if="node.kind === 'scalar'">
        <Select
          v-if="node.valueType === 'boolean'"
          :model-value="String(node.value)"
          :disabled="disabled"
          @update:model-value="
            change((n) => {
              if (n.kind === 'scalar') n.value = $event === 'true';
            })
          "
          ><SelectTrigger aria-label="Значение"><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem value="true">Да</SelectItem
              ><SelectItem value="false">Нет</SelectItem></SelectGroup
            ></SelectContent
          ></Select
        >
        <Input
          v-else
          :model-value="String(node.value)"
          :disabled="disabled"
          aria-label="Значение"
          @update:model-value="
            change((n) => {
              if (n.kind === 'scalar') n.value = String($event);
            })
          "
        />
      </template>
      <template v-else>
        <div
          v-for="(item, index) in node.items"
          :key="index"
          class="flex gap-2"
        >
          <Select
            v-if="node.itemType === 'boolean'"
            :model-value="item.kind === 'scalar' ? String(item.value) : ''"
            :disabled="disabled"
            @update:model-value="
              change((n) => {
                if (n.kind === 'collection')
                  n.items[index] = {
                    kind: 'scalar',
                    valueType: n.itemType,
                    value: $event === 'true',
                  };
              })
            "
            ><SelectTrigger aria-label="Элемент списка"
              ><SelectValue /></SelectTrigger
            ><SelectContent
              ><SelectGroup
                ><SelectItem value="true">Да</SelectItem
                ><SelectItem value="false">Нет</SelectItem></SelectGroup
              ></SelectContent
            ></Select
          >
          <Input
            v-else
            :model-value="item.kind === 'scalar' ? String(item.value) : ''"
            :disabled="disabled"
            aria-label="Элемент списка"
            @update:model-value="
              change((n) => {
                if (n.kind === 'collection')
                  n.items[index] = {
                    kind: 'scalar',
                    valueType: n.itemType,
                    value: String($event),
                  };
              })
            "
          />
          <Button
            type="button"
            variant="outline"
            :disabled="disabled"
            @click="
              change((n) => {
                if (n.kind === 'collection') n.items.splice(index, 1);
              })
            "
            >Удалить</Button
          >
        </div>
        <Button
          type="button"
          variant="outline"
          :disabled="
            disabled || node.items.length >= metadata.maxCollectionItems
          "
          @click="
            change((n) => {
              if (n.kind === 'collection')
                n.items.push({
                  kind: 'scalar',
                  valueType: n.itemType,
                  value: n.itemType === 'boolean' ? false : '',
                });
            })
          "
          >Добавить значение</Button
        >
      </template>
    </template>
    <template v-if="node.kind === 'arithmetic' || node.kind === 'comparison'">
      <Field
        v-for="key in node.kind === 'arithmetic' && node.operator === 'NEGATE'
          ? (['operand'] as const)
          : (['left', 'right'] as const)"
        :key="key"
        ><FieldLabel>{{
          key === "left" ? "Слева" : key === "right" ? "Справа" : "Значение"
        }}</FieldLabel
        ><CalculationNodeEditor
          v-if="key in node"
          :node="
            (
              node as {
                left?: SchemaNode;
                right?: SchemaNode;
                operand?: SchemaNode;
              }
            )[key]!
          "
          :category="node.kind === 'comparison' ? 'value' : 'number'"
          :metadata="metadata"
          :disabled="nestedDisabled"
          :depth="depth + 1"
          :path="[...path, key]"
          :issues="issues"
          @change="child(key, $event)"
      /></Field>
    </template>
    <template v-if="node.kind === 'function' || node.kind === 'logical'">
      <div
        v-for="(item, index) in node.kind === 'function'
          ? node.arguments
          : node.operands"
        :key="index"
        class="flex min-w-0 flex-col gap-2"
      >
        <CalculationNodeEditor
          :node="item"
          :category="node.kind === 'logical' ? 'condition' : 'number'"
          :metadata="metadata"
          :disabled="nestedDisabled"
          :depth="depth + 1"
          :path="[
            ...path,
            node.kind === 'function' ? 'arguments' : 'operands',
            index,
          ]"
          :issues="issues"
          @change="listChild(index, $event)"
        /><Button
          v-if="
            node.kind === 'function'
              ? node.arguments.length > 2
              : node.operands.length > 1
          "
          type="button"
          variant="outline"
          :disabled="disabled"
          @click="listRemove(index)"
          >Удалить аргумент</Button
        >
      </div>
      <Button
        v-if="
          node.kind === 'function'
            ? node.function !== 'ABS'
            : node.operator !== 'NOT'
        "
        type="button"
        variant="outline"
        :disabled="
          nestedDisabled ||
          (node.kind === 'function'
            ? node.arguments.length
            : node.operands.length) >= metadata.maxNodes
        "
        @click="
          change((n) => {
            if (n.kind === 'function') n.arguments.push(newNode('decimal'));
            else if (n.kind === 'logical') n.operands.push(newNode('presence'));
          })
        "
        >Добавить аргумент</Button
      >
    </template>
    <FieldError v-for="(issue, index) in messages" :key="index">{{
      issue.message
    }}</FieldError>
  </div>
</template>
