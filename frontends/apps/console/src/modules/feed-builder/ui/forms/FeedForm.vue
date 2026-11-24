<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import type { FeedDraft, FeedFieldErrors } from "../../model/feed.types";
import { feedValidationLabels } from "../../model/feed.constants";
import { validateFeedDraft } from "../../model/feed.draft";
const props = defineProps<{
  draft: FeedDraft;
  busy: boolean;
  dirty: boolean;
  creating: boolean;
  readonly: boolean;
  blocked: boolean;
  errors: FeedFieldErrors;
}>();
const emit = defineEmits<{
  change: [draft: FeedDraft];
  submit: [];
  reset: [];
}>();
const form = ref<HTMLFormElement>(),
  localErrors = ref<FeedFieldErrors>({});
const errors = computed(() => ({ ...props.errors, ...localErrors.value }));
watch(
  () => props.draft,
  () => {
    localErrors.value = {};
  },
);
function change<K extends keyof FeedDraft>(key: K, value: FeedDraft[K]): void {
  localErrors.value = {};
  emit("change", { ...props.draft, [key]: value });
}
async function submit(): Promise<void> {
  if (props.busy || props.readonly || props.blocked) return;
  localErrors.value = validateFeedDraft(props.draft);
  if (Object.keys(localErrors.value).length) {
    await nextTick();
    form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
    return;
  }
  emit("submit");
}
</script>
<template>
  <form
    ref="form"
    class="flex flex-col gap-6"
    novalidate
    @submit.prevent="submit"
  >
    <FieldGroup>
      <FieldSet :disabled="busy || readonly">
        <FieldLegend>Основные настройки</FieldLegend>
        <FieldGroup>
          <Field :data-invalid="!!errors.name">
            <FieldLabel for="feed-name">Название</FieldLabel>
            <Input
              id="feed-name"
              :model-value="draft.name"
              :aria-invalid="!!errors.name"
              :aria-describedby="errors.name ? 'feed-name-error' : undefined"
              maxlength="255"
              autocomplete="off"
              @update:model-value="change('name', String($event))"
            />
            <FieldError v-if="errors.name" id="feed-name-error">{{
              errors.name
            }}</FieldError>
          </Field>
          <Field :data-invalid="!!errors.code">
            <FieldLabel for="feed-code">Код</FieldLabel>
            <Input
              id="feed-code"
              :model-value="draft.code"
              :aria-invalid="!!errors.code"
              :aria-describedby="
                errors.code ? 'feed-code-error' : 'feed-code-help'
              "
              maxlength="64"
              autocomplete="off"
              spellcheck="false"
              @update:model-value="change('code', String($event))"
            />
            <FieldDescription id="feed-code-help"
              >Уникальный код: строчные латинские буквы, цифры, _ и -.
              Сохраняется за фидом после архивации.</FieldDescription
            >
            <FieldError v-if="errors.code" id="feed-code-error">{{
              errors.code
            }}</FieldError>
          </Field>
        </FieldGroup>
      </FieldSet>
      <FieldSet :disabled="busy || readonly">
        <FieldLegend>Формат выгрузки</FieldLegend>
        <FieldGroup>
          <Field :data-invalid="!!errors.format">
            <FieldLabel id="feed-format-label">Формат файла</FieldLabel>
            <ToggleGroup
              type="single"
              variant="outline"
              :model-value="draft.format"
              :disabled="busy || readonly"
              aria-labelledby="feed-format-label"
              :aria-invalid="!!errors.format"
              @update:model-value="
                ($event === 'csv' || $event === 'xml') &&
                change('format', $event)
              "
            >
              <ToggleGroupItem value="csv" aria-label="CSV"
                >CSV</ToggleGroupItem
              >
              <ToggleGroupItem value="xml" aria-label="XML"
                >XML</ToggleGroupItem
              >
            </ToggleGroup>
            <FieldDescription
              >Один фид формирует один формат файла.</FieldDescription
            >
            <FieldError v-if="errors.format">{{ errors.format }}</FieldError>
          </Field>
          <template v-if="draft.format === 'csv'">
            <Field :data-invalid="!!errors.delimiter">
              <FieldLabel for="feed-delimiter">Разделитель CSV</FieldLabel>
              <Select
                :model-value="
                  draft.delimiter === '\t' ? 'tab' : draft.delimiter
                "
                :disabled="busy || readonly"
                @update:model-value="
                  change('delimiter', $event === 'tab' ? '\t' : String($event))
                "
              >
                <SelectTrigger id="feed-delimiter"
                  ><SelectValue
                /></SelectTrigger>
                <SelectContent
                  ><SelectGroup>
                    <SelectItem value=",">Запятая (,)</SelectItem
                    ><SelectItem value=";">Точка с запятой (;)</SelectItem
                    ><SelectItem value="tab">Табуляция</SelectItem
                    ><SelectItem value="|">Вертикальная черта (|)</SelectItem>
                    <SelectItem
                      v-if="![',', ';', '\t', '|'].includes(draft.delimiter)"
                      :value="draft.delimiter"
                      >{{ draft.delimiter }}</SelectItem
                    >
                  </SelectGroup></SelectContent
                >
              </Select>
              <FieldError v-if="errors.delimiter">{{
                errors.delimiter
              }}</FieldError>
            </Field>
            <Field orientation="horizontal">
              <Checkbox
                id="feed-header"
                :model-value="draft.includeHeader"
                :disabled="busy || readonly"
                @update:model-value="change('includeHeader', $event === true)"
              />
              <FieldLabel for="feed-header"
                >Добавлять строку заголовков</FieldLabel
              >
            </Field>
          </template>
          <template v-if="draft.format === 'xml'">
            <Field :data-invalid="!!errors.rootName">
              <FieldLabel for="feed-root-name">Корневой элемент XML</FieldLabel>
              <Input
                id="feed-root-name"
                :model-value="draft.rootName"
                :aria-invalid="!!errors.rootName"
                maxlength="128"
                spellcheck="false"
                @update:model-value="change('rootName', String($event))"
              />
              <FieldError v-if="errors.rootName">{{
                errors.rootName
              }}</FieldError>
            </Field>
            <Field :data-invalid="!!errors.itemName">
              <FieldLabel for="feed-item-name">Элемент товара XML</FieldLabel>
              <Input
                id="feed-item-name"
                :model-value="draft.itemName"
                :aria-invalid="!!errors.itemName"
                maxlength="128"
                spellcheck="false"
                @update:model-value="change('itemName', String($event))"
              />
              <FieldError v-if="errors.itemName">{{
                errors.itemName
              }}</FieldError>
            </Field>
          </template>
          <Field :data-invalid="!!errors.validationPolicy">
            <FieldLabel for="feed-validation-policy">Проверка данных</FieldLabel>
            <Select
              :model-value="draft.validationPolicy"
              :disabled="busy || readonly"
              @update:model-value="
                ($event === 'STRICT' || $event === 'SKIP_INVALID') &&
                change('validationPolicy', $event)
              "
            >
              <SelectTrigger
                id="feed-validation-policy"
                :aria-invalid="!!errors.validationPolicy"
                :aria-describedby="
                  errors.validationPolicy
                    ? 'feed-validation-error'
                    : 'feed-validation-help'
                "
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="STRICT">{{ feedValidationLabels.STRICT }}</SelectItem>
                <SelectItem value="SKIP_INVALID">{{ feedValidationLabels.SKIP_INVALID }}</SelectItem>
              </SelectContent>
            </Select>
            <FieldError v-if="errors.validationPolicy" id="feed-validation-error">
              {{ errors.validationPolicy }}
            </FieldError>
            <FieldDescription v-else id="feed-validation-help">
              {{
                draft.validationPolicy === 'STRICT'
                  ? 'Ошибка любой позиции блокирует обновление файла.'
                  : 'Позиции с ошибками пропускаются. Если отклонены все позиции, прежний файл сохраняется.'
              }}
            </FieldDescription>
          </Field>
        </FieldGroup>
      </FieldSet>
      <Field>
        <FieldLabel>Обработка товаров</FieldLabel>
        <FieldDescription
          >Простые товары и выбранные варианты выгружаются отдельными строками.
          Кодировка UTF-8.</FieldDescription
        >
      </Field>
    </FieldGroup>
    <div v-if="!readonly" class="flex flex-wrap gap-2">
      <Button
        type="submit"
        :disabled="busy || blocked || !draft.format || (!creating && !dirty)"
        >{{
          busy ? "Сохраняем…" : creating ? "Создать фид" : "Сохранить настройки"
        }}</Button
      >
      <Button
        v-if="dirty && !creating && !blocked"
        type="button"
        variant="outline"
        :disabled="busy"
        @click="emit('reset')"
        >Отменить изменения</Button
      >
    </div>
  </form>
</template>
