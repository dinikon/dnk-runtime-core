<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type { RepresentationPreview } from "../../model/representation.types";
import { representationIssueMessage } from "../../model/representation.errors";
import RepresentationTargetCard from "./RepresentationTargetCard.vue";

const props = defineProps<{
  preview?: RepresentationPreview;
  locale: string;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{ retry: [] }>();
const selectedLocale = ref(props.locale);
const view = ref<"effective" | "catalog">("effective");
const locale = computed({
  get: () =>
    props.preview?.locales.includes(selectedLocale.value)
      ? selectedLocale.value
      : (props.preview?.locales[0] ?? ""),
  set: (value: string) => {
    selectedLocale.value = value;
  },
});
const localeId = useId();
</script>

<template>
  <section
    class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4"
    :aria-busy="loading"
  >
    <p class="text-sm text-muted-foreground">
      Контент из текущего Catalog. Просмотр не отправляет изменения на площадку.
    </p>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-2"
        >{{ error
        }}<Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="loading"
          @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <div
      v-if="loading && !preview"
      role="status"
      aria-label="Формирование представления"
      class="space-y-4"
    >
      <Skeleton class="h-10 w-full" /><Skeleton class="h-64 w-full" />
    </div>
    <template v-if="preview">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <label class="space-y-1 text-sm font-medium"
          >Показать<select
            v-model="view"
            aria-label="Источник предпросмотра"
            class="block h-9 rounded-md border border-input bg-background px-3"
          >
            <option value="effective">Итог</option>
            <option value="catalog">Catalog</option>
          </select></label
        >
        <div class="space-y-1">
          <label :for="localeId" class="block text-sm font-medium"
            >Язык представления</label
          ><select
            :id="localeId"
            v-model="locale"
            class="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option v-for="code in preview.locales" :key="code" :value="code">
              {{ code }}
            </option>
          </select>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="loading"
          @click="emit('retry')"
          >{{ loading ? "Обновляем…" : "Обновить представление" }}</Button
        >
      </div>
      <Alert v-for="(issue, index) in preview.issues" :key="index"
        ><AlertDescription>{{
          representationIssueMessage(issue.code)
        }}</AlertDescription></Alert
      >
      <p v-if="!preview.targets.length" class="text-sm text-muted-foreground">
        В группе нет сопоставленных позиций для формирования контента.
      </p>
      <RepresentationTargetCard
        v-for="target in preview.targets"
        :key="target.publicationId"
        :target="target"
        :locale="locale"
        :view="view"
      />
    </template>
  </section>
</template>
