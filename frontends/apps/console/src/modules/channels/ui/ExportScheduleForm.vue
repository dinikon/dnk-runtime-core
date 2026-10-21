<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldLabel, FieldGroup } from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { ExportSchedule } from "../model/batch-export.types";
const props = defineProps<{
  schedule: ExportSchedule;
  pending: boolean;
  disabled: boolean;
  allowDaily: boolean;
  saveSequence: number;
}>();
const emit = defineEmits<{
  submit: [
    value: {
      enabled: boolean;
      hour: number;
      minute: number;
      timezone: string;
      expectedRevision: number;
    },
  ];
  dirty: [value: boolean];
}>();
const enabled = ref(props.schedule.enabled),
  time = ref(
    `${String(props.schedule.hour).padStart(2, "0")}:${String(props.schedule.minute).padStart(2, "0")}`,
  ),
  zone = ref(props.schedule.timezone),
  revision = ref(props.schedule.revision),
  dirty = ref(false);
function reset(): void {
  enabled.value = props.schedule.enabled;
  time.value = `${String(props.schedule.hour).padStart(2, "0")}:${String(props.schedule.minute).padStart(2, "0")}`;
  zone.value = props.schedule.timezone;
  revision.value = props.schedule.revision;
  dirty.value = false;
  emit("dirty", false);
}
watch(
  () => props.schedule,
  (value) => {
    if (!dirty.value) {
      enabled.value = value.enabled;
      time.value = `${String(value.hour).padStart(2, "0")}:${String(value.minute).padStart(2, "0")}`;
      zone.value = value.timezone;
      revision.value = value.revision;
    }
  },
);
watch(() => props.saveSequence, reset);
function changed(): void {
  dirty.value = true;
  emit("dirty", true);
}
function submit(): void {
  const [hour, minute] = time.value.split(":").map(Number);
  if (hour === undefined || minute === undefined || !zone.value.trim()) return;
  emit("submit", {
    enabled: enabled.value,
    hour,
    minute,
    timezone: zone.value.trim(),
    expectedRevision: revision.value,
  });
}
</script>
<template>
  <form class="flex flex-col gap-3" @submit.prevent="submit">
    <FieldGroup class="grid gap-3 sm:grid-cols-3">
      <Field
        ><FieldLabel for="export-mode">Режим обновления</FieldLabel
        ><NativeSelect
          id="export-mode"
          :model-value="enabled ? 'daily' : 'manual'"
          :disabled="pending || disabled"
          @update:model-value="
            (value) => {
              enabled = value === 'daily';
              changed();
            }
          "
          ><NativeSelectOption value="manual">Только вручную</NativeSelectOption
          ><NativeSelectOption value="daily" :disabled="!allowDaily"
            >Ежедневно</NativeSelectOption
          ></NativeSelect
        ></Field
      >
      <Field
        ><FieldLabel for="export-time">Время запуска</FieldLabel
        ><Input
          id="export-time"
          v-model="time"
          type="time"
          required
          :disabled="pending || disabled || !enabled"
          @input="changed"
      /></Field>
      <Field
        ><FieldLabel for="export-zone">Часовой пояс</FieldLabel
        ><Input
          id="export-zone"
          v-model="zone"
          maxlength="100"
          placeholder="Europe/Kyiv"
          required
          :disabled="pending || disabled || !enabled"
          @input="changed"
      /></Field>
    </FieldGroup>
    <div class="flex flex-wrap items-center gap-3">
      <Button
        variant="outline"
        type="submit"
        :disabled="pending || disabled || !dirty"
        >{{ pending ? "Сохраняем…" : "Сохранить расписание" }}</Button
      ><span v-if="dirty" class="text-muted-foreground text-xs"
        >Есть несохранённые изменения</span
      >
    </div>
  </form>
</template>
