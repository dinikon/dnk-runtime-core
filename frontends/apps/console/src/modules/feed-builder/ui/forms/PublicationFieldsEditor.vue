<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import type {
  PublicationField,
  PublicationFields,
  PublicationOverrideDraft,
} from "../../model/publication-fields.types";

const props = defineProps<{
  data?: PublicationFields;
  draft?: PublicationOverrideDraft;
  activeField?: PublicationField;
  conflict: boolean;
  pending: boolean;
  loading: boolean;
  loadError: string;
  error?: { fieldId: string; message: string };
}>();
const emit = defineEmits<{
  edit: [field: PublicationField];
  update: [value: string];
  save: [];
  reset: [fieldId: string];
  cancel: [];
  accept: [];
  refresh: [];
}>();

const rows = computed(() => {
  const fields = props.data?.fields ?? [];
  const missing = props.draft?.field;
  return missing && !fields.some((field) => field.id === missing.id)
    ? [...fields, missing]
    : fields;
});
const length = computed(() => Array.from(props.draft?.value ?? "").length);
const invalidLength = computed(() => {
  const max = props.draft?.field.maxLength;
  return max != null && length.value > max;
});
const inputId = computed(
  () => `publication-override-${props.draft?.field.id ?? ""}`,
);

function input(event: Event): void {
  emit(
    "update",
    (event.target as HTMLInputElement | HTMLTextAreaElement).value,
  );
}
</script>

<template>
  <section class="grid gap-3" aria-label="Поля публикации">
    <h3 class="font-medium">Поля публикации</h3>
    <div v-if="loadError" class="flex items-center gap-3">
      <p role="alert" class="text-sm text-destructive">{{ loadError }}</p>
      <Button
        type="button"
        size="sm"
        variant="outline"
        @click="emit('refresh')"
      >
        Обновить
      </Button>
    </div>
    <p v-else-if="loading" role="status" class="text-sm text-muted-foreground">
      Загрузка полей…
    </p>
    <template v-if="data">
      <p v-if="!data.fields.length" class="text-sm text-muted-foreground">
        В схеме фида пока нет полей.
      </p>
      <p
        v-else-if="!data.sourceAvailable"
        class="text-sm text-muted-foreground"
      >
        Значения Catalog для этой позиции недоступны.
      </p>
      <article
        v-for="field in rows"
        :key="field.id"
        class="grid gap-2 rounded-md border p-3"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h4 class="min-w-0 break-all text-sm font-medium">
            {{ field.label }}
          </h4>
          <span v-if="field.hasOverride" class="text-xs text-muted-foreground">
            Своё значение
          </span>
        </div>
        <dl class="grid min-w-0 gap-2 text-sm sm:grid-cols-2">
          <div class="min-w-0">
            <dt class="text-xs text-muted-foreground">Значение фида</dt>
            <dd class="whitespace-pre-wrap break-words">
              {{ field.originalValue ?? "—" }}
            </dd>
            <dd
              v-for="issue in field.originalIssues"
              :key="issue"
              class="text-xs text-destructive"
            >
              {{ issue }}
            </dd>
          </div>
          <div v-if="field.hasOverride" class="min-w-0">
            <dt class="text-xs text-muted-foreground">Итоговое значение</dt>
            <dd class="whitespace-pre-wrap break-words">
              {{ field.resolvedValue ?? "—" }}
            </dd>
            <dd
              v-for="issue in field.issues"
              :key="issue"
              class="text-xs text-destructive"
            >
              {{ issue }}
            </dd>
          </div>
        </dl>
        <div
          v-if="!data.readonly && draft?.field.id !== field.id"
          class="flex flex-wrap gap-2"
        >
          <Button
            type="button"
            size="sm"
            variant="outline"
            :disabled="pending || !!draft || !!loadError"
            @click="emit('edit', field)"
          >
            {{
              field.hasOverride
                ? "Изменить своё значение"
                : "Задать своё значение"
            }}
          </Button>
          <Button
            v-if="field.hasOverride"
            type="button"
            size="sm"
            variant="ghost"
            :disabled="pending || !!draft || !!loadError"
            @click="emit('reset', field.id)"
          >
            Вернуть значение фида
          </Button>
        </div>
        <p
          v-if="error?.fieldId === field.id && draft?.field.id !== field.id"
          role="alert"
          class="text-sm text-destructive"
        >
          {{ error.message }}
        </p>
        <form
          v-if="draft?.field.id === field.id"
          class="grid min-w-0 gap-2 rounded-md border p-3"
          @submit.prevent="emit('save')"
        >
          <label :for="inputId" class="break-words text-sm font-medium">
            Своё значение для поля «{{ draft.field.label }}»
          </label>
          <textarea
            v-if="draft.field.kind === 'text'"
            :id="inputId"
            :value="draft.value"
            rows="3"
            :disabled="pending"
            :aria-invalid="invalidLength || error?.fieldId === draft.field.id"
            :aria-describedby="`${inputId}-rules`"
            class="w-full rounded-md border bg-background p-2 text-sm"
            @input="input"
          />
          <input
            v-else
            :id="inputId"
            type="text"
            :inputmode="draft.field.kind === 'money' ? 'decimal' : 'text'"
            :value="draft.value"
            :disabled="pending"
            :aria-invalid="invalidLength || error?.fieldId === draft.field.id"
            :aria-describedby="`${inputId}-rules`"
            class="w-full min-w-0 rounded-md border bg-background p-2 text-sm"
            @input="input"
          />
          <div
            :id="`${inputId}-rules`"
            class="flex flex-wrap gap-2 text-xs text-muted-foreground"
          >
            <span v-if="draft.field.required">Обязательное поле</span>
            <span v-if="draft.field.kind === 'money'"
              >Десятичная сумма{{
                draft.field.currency ? ` · ${draft.field.currency}` : ""
              }}</span
            >
            <span v-if="draft.field.minAmount !== null"
              >От {{ draft.field.minAmount }}</span
            >
            <span v-if="draft.field.maxAmount !== null"
              >До {{ draft.field.maxAmount }}</span
            >
            <span v-if="draft.field.minLength !== null"
              >От {{ draft.field.minLength }} символов</span
            >
            <span
              v-if="draft.field.maxLength !== null"
              :class="{ 'text-destructive': invalidLength }"
            >
              {{ length }} / {{ draft.field.maxLength }} символов
            </span>
          </div>
          <p
            v-if="conflict"
            role="status"
            class="text-sm text-muted-foreground"
          >
            {{
              activeField
                ? "Данные изменились. Сверьте ввод с актуальным полем."
                : "Поля больше нет в сохранённой схеме. Введённое значение можно скопировать."
            }}
          </p>
          <p
            v-if="error?.fieldId === draft.field.id"
            role="alert"
            class="text-sm text-destructive"
          >
            {{ error.message }}
          </p>
          <div class="flex flex-wrap gap-2">
            <Button
              v-if="conflict && activeField"
              type="button"
              variant="outline"
              size="sm"
              :disabled="pending || data?.readonly || !!loadError"
              @click="emit('accept')"
            >
              Использовать актуальные правила
            </Button>
            <Button
              v-else
              type="submit"
              size="sm"
              :disabled="
                pending ||
                conflict ||
                !activeField ||
                data?.readonly ||
                invalidLength ||
                !!loadError
              "
            >
              {{ pending ? "Сохраняем…" : "Сохранить" }}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              :disabled="pending"
              @click="emit('cancel')"
              >Отмена</Button
            >
          </div>
        </form>
      </article>
    </template>
  </section>
</template>
