<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ContentFeed } from "../../model/content-feed.types";
const props = defineProps<{
  feed: ContentFeed | null;
  busy: boolean;
  locked: boolean;
  savedVersion: number;
}>();
const emit = defineEmits<{
  save: [sourceUrl: string, expectedRevision: number];
  dirty: [value: boolean];
}>();
const source = ref(""),
  baseRevision = ref(props.feed?.revision ?? 0);
const dirty = computed(() => !!source.value.trim());
const changed = computed(
  () => dirty.value && baseRevision.value !== (props.feed?.revision ?? 0),
);
watch(dirty, (v) => emit("dirty", v), { immediate: true });
watch(
  () => props.feed?.revision,
  () => {
    if (!dirty.value) baseRevision.value = props.feed?.revision ?? 0;
  },
);
watch(
  () => props.savedVersion,
  () => {
    source.value = "";
    baseRevision.value = props.feed?.revision ?? 0;
  },
);
function save(): void {
  emit("save", source.value.trim(), baseRevision.value);
}
</script>
<template>
  <form @submit.prevent="save">
    <FieldGroup>
      <Field :data-disabled="busy || locked">
        <FieldLabel for="feed-source-url">Исходный XML</FieldLabel>
        <Input
          id="feed-source-url"
          v-model="source"
          type="url"
          required
          autocomplete="off"
          :spellcheck="false"
          placeholder="https://supplier.example/catalog.xml"
          :disabled="busy || locked"
        />
        <FieldDescription>{{
          feed
            ? "Источник сохранён. Для замены введите новую ссылку целиком."
            : "Полный каталог Prom YML. Сопоставленные позиции получат контент из разрешённых представлений."
        }}</FieldDescription>
      </Field>
      <Alert v-if="locked"
        ><AlertDescription
          >Источник можно заменить после завершения импорта или выяснения его
          результата.</AlertDescription
        ></Alert
      >
      <Alert v-if="changed"
        ><AlertDescription class="flex flex-col gap-2"
          >Настройки изменились. Введённая ссылка сохранена.
          <Button
            type="button"
            variant="outline"
            :disabled="busy || locked"
            @click="baseRevision = feed?.revision ?? 0"
            >Сохранить мой источник поверх актуальных настроек</Button
          >
        </AlertDescription></Alert
      >
      <div class="flex flex-wrap gap-2">
        <Button type="submit" :disabled="busy || locked || !dirty || changed">{{
          feed ? "Сохранить источник" : "Создать фид"
        }}</Button>
      </div>
    </FieldGroup>
  </form>
</template>
