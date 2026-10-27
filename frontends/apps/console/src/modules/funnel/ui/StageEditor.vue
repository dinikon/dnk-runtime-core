<script setup lang="ts">
import { ref, useId } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  canRemoveStage,
  moveStage,
  stageGroups,
  stagePalette,
} from "../model/funnel.draft";
import type { FunnelStageDraft, StageKind } from "../model/funnel.types";
const props = defineProps<{
  modelValue: FunnelStageDraft[];
  disabled?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: FunnelStageDraft[]];
}>();
const dragged = ref<number | null>(null),
  uid = useId();
function change(key: string, field: "name" | "color", value: string): void {
  if (props.disabled) return;
  emit(
    "update:modelValue",
    props.modelValue.map((s) =>
      s.clientKey === key ? { ...s, [field]: value } : s,
    ),
  );
}
function indexOf(stage: FunnelStageDraft): number {
  return props.modelValue.findIndex((s) => s.clientKey === stage.clientKey);
}
function move(from: number, to: number): void {
  if (!props.disabled)
    emit("update:modelValue", moveStage(props.modelValue, from, to));
}
function remove(stage: FunnelStageDraft): void {
  if (!props.disabled && canRemoveStage(props.modelValue, stage.clientKey))
    emit(
      "update:modelValue",
      props.modelValue.filter((s) => s.clientKey !== stage.clientKey),
    );
}
function add(kind: StageKind): void {
  if (props.disabled || props.modelValue.length >= 50 || kind === "won") return;
  const stage: FunnelStageDraft = {
    clientKey: crypto.randomUUID(),
    name: "Новая стадия",
    kind,
    color: kind === "lost" ? "#EF4444" : "#64748B",
  };
  const at =
    kind === "in_progress"
      ? props.modelValue.findIndex((s) => s.kind !== kind)
      : props.modelValue.length;
  const stages = [...props.modelValue];
  stages.splice(at < 0 ? stages.length : at, 0, stage);
  emit("update:modelValue", stages);
}
function validColor(color: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(color);
}
</script>
<template>
  <div class="flex flex-col gap-6">
    <section
      v-for="group in stageGroups"
      :key="group.kind"
      class="flex flex-col gap-3"
      :aria-label="group.label"
    >
      <h2 class="text-lg font-semibold">{{ group.label }}</h2>
      <article
        v-for="stage in modelValue.filter((s) => s.kind === group.kind)"
        :key="stage.clientKey"
        class="flex flex-col gap-3 rounded-lg border p-4"
        @dragover.prevent
        @drop.prevent="
          dragged !== null && move(dragged, indexOf(stage));
          dragged = null;
        "
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span
              class="size-4 shrink-0 rounded-full border"
              :style="{
                backgroundColor: validColor(stage.color)
                  ? stage.color
                  : 'transparent',
              }"
              aria-hidden="true"
            />
            <span class="break-all font-medium">{{ stage.name }}</span>
            <Badge v-if="indexOf(stage) === 0" variant="secondary"
              >Начальная</Badge
            >
          </div>
          <div class="flex gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="
                disabled || modelValue[indexOf(stage) - 1]?.kind !== stage.kind
              "
              :aria-label="'Поднять стадию ' + stage.name"
              @click="move(indexOf(stage), indexOf(stage) - 1)"
              >↑</Button
            >
            <Button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="
                disabled || modelValue[indexOf(stage) + 1]?.kind !== stage.kind
              "
              :aria-label="'Опустить стадию ' + stage.name"
              @click="move(indexOf(stage), indexOf(stage) + 1)"
              >↓</Button
            >
            <Button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="
                disabled || !canRemoveStage(modelValue, stage.clientKey)
              "
              :title="
                stage.kind === 'won'
                  ? 'Успешная стадия обязательна'
                  : 'Должна остаться хотя бы одна стадия этого типа'
              "
              :aria-label="'Удалить стадию ' + stage.name"
              @click="remove(stage)"
              >Удалить</Button
            >
            <button
              type="button"
              :draggable="!disabled && stage.kind !== 'won'"
              :disabled="disabled || stage.kind === 'won'"
              :aria-label="'Перетащить стадию ' + stage.name"
              class="cursor-grab rounded px-2"
              @dragstart="
                dragged = indexOf(stage);
                $event.dataTransfer?.setData('text/plain', stage.clientKey);
              "
              @dragend="dragged = null"
            >
              ⠿
            </button>
          </div>
        </div>
        <FieldGroup>
          <Field
            ><FieldLabel :for="uid + stage.clientKey + 'name'"
              >Название *</FieldLabel
            >
            <Input
              :id="uid + stage.clientKey + 'name'"
              :model-value="stage.name"
              required
              maxlength="100"
              :disabled="disabled"
              @update:model-value="
                change(stage.clientKey, 'name', String($event))
              "
            />
          </Field>
          <Field :data-invalid="!validColor(stage.color) || undefined">
            <FieldLabel :for="uid + stage.clientKey + 'hex'"
              >Цвет HEX</FieldLabel
            >
            <div class="flex items-center gap-2">
              <Input
                :id="uid + stage.clientKey + 'hex'"
                :model-value="stage.color"
                maxlength="7"
                pattern="#[0-9a-fA-F]{6}"
                :aria-invalid="!validColor(stage.color)"
                :disabled="disabled"
                @update:model-value="
                  change(stage.clientKey, 'color', String($event))
                "
              />
              <input
                type="color"
                :value="validColor(stage.color) ? stage.color : '#64748B'"
                :disabled="disabled"
                :aria-label="'Выбрать цвет стадии ' + stage.name"
                class="h-9 w-12 shrink-0 rounded border bg-background p-1"
                @input="
                  change(
                    stage.clientKey,
                    'color',
                    ($event.target as HTMLInputElement).value.toUpperCase(),
                  )
                "
              />
            </div>
            <div
              class="flex flex-wrap gap-2"
              role="group"
              :aria-label="'Палитра стадии ' + stage.name"
            >
              <button
                v-for="color in stagePalette"
                :key="color"
                type="button"
                class="size-7 rounded-full border-2 border-background ring-1 ring-border focus-visible:outline-2 focus-visible:outline-ring"
                :style="{ backgroundColor: color }"
                :aria-label="color"
                :aria-pressed="stage.color.toUpperCase() === color"
                :disabled="disabled"
                @click="change(stage.clientKey, 'color', color)"
              >
                <span
                  v-if="stage.color.toUpperCase() === color"
                  class="rounded bg-background px-0.5 text-xs text-foreground"
                  >✓</span
                >
              </button>
            </div>
            <p v-if="!validColor(stage.color)" class="text-sm text-destructive">
              Используйте формат #RRGGBB.
            </p>
          </Field>
        </FieldGroup>
      </article>
      <Button
        v-if="group.kind !== 'won'"
        type="button"
        variant="outline"
        :disabled="disabled || modelValue.length >= 50"
        @click="add(group.kind)"
        >{{
          group.kind === "lost"
            ? "Добавить неуспешную стадию"
            : "Добавить рабочую стадию"
        }}</Button
      >
    </section>
    <p class="text-sm text-muted-foreground">
      Тип стадии задаётся при создании. Первая рабочая стадия применяется к
      новым назначениям и переносу из удалённых стадий.
    </p>
  </div>
</template>
