<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import FeedHeader from "../ui/page/FeedHeader.vue";
import FeedSections from "../ui/page/FeedSections.vue";
import FeedStatus from "../ui/item/FeedStatus.vue";
import SchemaFieldsList from "../ui/results/SchemaFieldsList.vue";
import CalculationPreviewPanel from "../ui/results/CalculationPreviewPanel.vue";
import { calculationErrorMessage } from "../model/feed-calculation.errors";
import { useFeedCalculationPreview } from "../model/use-feed-calculation-preview";
import { fieldCanPreview, fieldIsReadonly } from "../model/feed-schema.draft";
import { useFeedCategoryTree } from "../model/feed-categories.queries";
import FieldNodeForm from "../ui/forms/FieldNodeForm.vue";
import { useFeedSchemaEditor } from "../model/use-feed-schema-editor";
import { useFeed } from "../model/feed.queries";
import { useFeedEditorNavigation } from "../model/use-feed-editor-navigation";
import { feedListReturnTo, feedSectionRoutes } from "../model/feed.navigation";
import { feedErrorMessage } from "../model/feed.errors";
import { SchemaApiError, type SchemaIssue } from "../model/feed-schema.types";
import { FeedApiError } from "../model/feed.types";
const route = useRoute(),
  router = useRouter();
const id = computed(() => String(route.params.id ?? ""));
const editor = useFeedSchemaEditor(id),
  feed = useFeed(id);
const categorySection = ref(false);
const sections = [
  { categories: false, label: "Поля предложения" },
  { categories: true, label: "Категории" },
] as const;
const visibleFields = computed(() =>
  (editor.draft.value?.fields ?? []).filter(
    (field) => !categorySection.value || field.typeDefinition.kind === "category",
  ),
);
watch(id, () => { categorySection.value = false; });
watch(editor.selected, (field) => {
  if (field && field.typeDefinition.kind !== "category") categorySection.value = false;
});
function selectSection(categories: boolean): void {
  categorySection.value = categories;
  editor.selectedId.value = visibleFields.value[0]?.id ?? "";
}
function moveVisibleField(identifier: string, delta: number): void {
  const visibleIndex = visibleFields.value.findIndex((field) => field.id === identifier);
  const target = visibleFields.value[visibleIndex + delta];
  const fields = editor.draft.value?.fields;
  if (!target || !fields) return;
  editor.move(identifier, fields.indexOf(target) - fields.findIndex((field) => field.id === identifier));
}
const xmlItemName = computed(() => {
  const settings = feed.data.value?.exportSettings.formatSettings;
  return settings?.format === "xml" ? settings.itemName : undefined;
});
useFeedEditorNavigation(editor.dirty, editor.busy);
const exportedItemName = computed(() =>
  xmlItemName.value && editor.draft.value?.fields.some(
    field => field.export.enabled && field.export.document?.parent === "SHOP",
  ) ? "offer" : xmlItemName.value,
);
const catalogCategories = useFeedCategoryTree(
  computed(() => {
    const definition = editor.selected.value?.typeDefinition;
    return definition?.kind === "category" ? definition.locale : undefined;
  }),
);
const returnTo = computed(() => feedListReturnTo(route.query.returnTo));
const queryError = computed(
  () => editor.query.error.value || editor.metadata.error.value,
);
const errorMessage = computed(() => {
  const error = editor.error.value;
  if (!error) return "";
  if (error instanceof FeedApiError && error.status === 422)
    return "Схема не сохранена. Исправьте отмеченные настройки.";
  if (error instanceof FeedApiError && error.status === 413)
    return "Схема превышает допустимый размер.";
  if (error instanceof FeedApiError && error.status === 409)
    return "Feed изменён или архивирован. Ваш ввод сохранён.";
  return feedErrorMessage(error);
});
function issueFieldId(issue: SchemaIssue): string | undefined {
  if (issue.fieldId) return issue.fieldId;
  const fieldsPosition = issue.path.indexOf("fields");
  const index = issue.path[fieldsPosition + 1];
  if (fieldsPosition >= 0 && typeof index === "number")
    return editor.draft.value?.fields[index]?.id;
}
const fieldIssues = computed(() =>
  editor.issues.value.map((issue) => ({ ...issue, fieldId: issueFieldId(issue) })),
);
const selectedIssues = computed(() =>
  fieldIssues.value.filter((issue) => issue.fieldId === editor.selectedId.value),
);
const blocked = computed(
  () => editor.busy.value || editor.conflict.value || editor.readonly.value,
);
const previewBlocked = computed(
  () =>
    blocked.value ||
    (!!editor.selected.value && fieldIsReadonly(editor.selected.value)),
);
const preview = useFeedCalculationPreview(
  id,
  editor.baseVersion,
  editor.selected,
  editor.metadata.data,
  previewBlocked,
);
watch(preview.error, (error) => {
  if (error instanceof FeedApiError && error.status === 409)
    editor.conflict.value = true;
});
const previewError = computed(() =>
  calculationErrorMessage(preview.error.value),
);
const previewIssues = computed(() =>
  preview.error.value instanceof SchemaApiError
    ? preview.error.value.issues
    : [],
);
const sourceError = computed(
  () =>
    preview.products.error.value ||
    (preview.root.value?.kind === "variable"
      ? preview.variants.error.value
      : null),
);
function retryPreviewSources(): void {
  void preview.products.refetch();
  if (preview.root.value?.kind === "variable") void preview.variants.refetch();
}
function back(): void {
  void router.push(returnTo.value);
}
function settings(): void {
  void router.push({
    name: "feed-detail",
    params: { id: id.value },
    query: { returnTo: returnTo.value },
  });
}
function remove(identifier: string): void {
  const field = editor.draft.value?.fields.find((f) => f.id === identifier);
  if (field && window.confirm(`Удалить поле «${field.label}»?`))
    editor.remove(identifier);
}
async function reset(): Promise<void> {
  const context = editor.contextKey.value;
  if (editor.conflict.value) {
    const result = await editor.query.refetch();
    if (result.isError || context !== editor.contextKey.value) return;
  }
  if (
    !editor.dirty.value ||
    window.confirm("Загрузить актуальную схему и отменить ваши изменения?")
  )
    editor.reset();
}
async function save(): Promise<void> {
  if (await editor.save()) toast.success("Схема сохранена");
  else {
    await nextTick();
    document
      .querySelector<HTMLElement>('#feed-schema-editor [aria-invalid="true"]')
      ?.focus();
  }
}
</script>
<template>
  <Teleport to="#workspace-page-header" defer
    ><FeedHeader
      :title="feed.data.value?.name ?? 'Схема фида'"
      :archivable="false"
      :busy="editor.busy.value"
      @back="back"
  /></Teleport>
  <div
    id="feed-schema-editor"
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto pb-6"
  >
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-2xl font-semibold">Схема фида</h1>
        <FeedStatus
          v-if="editor.query.data.value"
          :status="editor.query.data.value.status"
        />
      </div>
      <div
        v-if="editor.draft.value && !editor.readonly.value"
        class="flex flex-wrap gap-2"
      >
        <Button
          type="button"
          :disabled="
            blocked || !editor.dirty.value || !editor.metadata.data.value
          "
          @click="save"
          >{{ editor.busy.value ? "Сохраняем…" : "Сохранить схему" }}</Button
        ><Button
          v-if="editor.dirty.value && !editor.conflict.value"
          type="button"
          variant="outline"
          :disabled="editor.busy.value"
          @click="reset"
          >Отменить изменения</Button
        >
      </div>
    </header>
    <FeedSections
      current="schema"
      :disabled="editor.busy.value"
      @navigate="
        $event === 'settings'
          ? settings()
          : $event !== 'schema' &&
            router.push({
              name: feedSectionRoutes[$event],
              params: { id },
              query: { returnTo },
            })
      "
    />
    <Alert v-if="queryError" variant="destructive"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
        >{{ feedErrorMessage(queryError)
        }}<Button
          type="button"
          variant="outline"
          :disabled="
            editor.query.isFetching.value || editor.metadata.isFetching.value
          "
          @click="
            editor.query.refetch();
            editor.metadata.refetch();
          "
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Alert v-if="editor.readonly.value"
      ><AlertDescription
        >Фид находится в архиве. Схема доступна только для
        просмотра.</AlertDescription
      ></Alert
    >
    <Alert v-if="errorMessage" variant="destructive"
      ><AlertDescription>{{ errorMessage }}</AlertDescription></Alert
    >
    <Alert v-if="editor.conflict.value && !editor.readonly.value"
      ><AlertDescription class="flex flex-col items-start gap-3"
        >Серверная версия отличается от открытой. Загрузите актуальную схему,
        чтобы продолжить редактирование.<Button
          type="button"
          variant="outline"
          :disabled="editor.busy.value || editor.query.isFetching.value"
          @click="reset"
          >Загрузить актуальную схему</Button
        ></AlertDescription
      ></Alert
    >
    <Alert v-if="editor.issues.value.length" variant="destructive"
      ><AlertDescription
        ><ul class="flex flex-col gap-2">
          <li v-for="(issue, index) in fieldIssues" :key="index">
            <button
              v-if="issue.fieldId"
              type="button"
              class="text-left underline underline-offset-4"
              @click="editor.selectedId.value = issue.fieldId"
            >
              {{ issue.message }}</button
            ><span v-else>{{ issue.message }}</span>
          </li>
        </ul></AlertDescription
      ></Alert
    >
    <div
      v-if="(!editor.draft.value || !editor.metadata.data.value) && !queryError"
      role="status"
      aria-label="Загрузка схемы"
      class="flex flex-col gap-3"
    >
      <Skeleton v-for="row in 6" :key="row" class="h-12 w-full" />
    </div>
    <div
      v-if="editor.metadata.data.value"
      role="group"
      aria-label="Раздел конструктора"
      class="flex flex-wrap gap-2"
    >
      <Button
        v-for="section in sections"
        :key="section.label"
        type="button"
        :aria-pressed="categorySection === section.categories"
        :variant="categorySection === section.categories ? 'secondary' : 'outline'"
        @click="selectSection(section.categories)"
      >{{ section.label }}</Button>
    </div>
    <div
      v-if="editor.draft.value && editor.metadata.data.value"
      class="grid min-w-0 grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(300px,400px)_minmax(0,1fr)]"
    >
      <SchemaFieldsList
        :fields="visibleFields"
        :total-fields="editor.draft.value.fields.length"
        :selected-id="editor.selectedId.value"
        :metadata="editor.metadata.data.value"
        :issues="fieldIssues"
        :categories="categorySection"
        :disabled="blocked"
        :readonly="editor.readonly.value"
        @select="editor.selectedId.value = $event"
        @add="editor.add"
        @move="moveVisibleField"
        @duplicate="editor.duplicate"
        @remove="remove"
      />
      <div v-if="editor.selected.value" class="flex min-w-0 flex-col gap-6">
        <FieldNodeForm
          :key="editor.selected.value.id"
          :field="editor.selected.value"
          :xml-item-name="exportedItemName"
          :catalog-categories="catalogCategories.data.value ?? []"
          :catalog-loading="catalogCategories.isFetching.value"
          :catalog-error="catalogCategories.isError.value"
          :saved-category-ids="editor.savedCategoryIds.value"
          @retry-catalog="catalogCategories.refetch()"
          :metadata="editor.metadata.data.value"
          :issues="[...selectedIssues, ...previewIssues]"
          :calculation-metadata="preview.metadata.data.value"
          :disabled="blocked"
          @change="editor.change"
        />
        <Alert v-if="preview.metadata.error.value" variant="destructive"
          ><AlertDescription class="flex flex-wrap items-center gap-2"
            >{{ feedErrorMessage(preview.metadata.error.value)
            }}<Button
              type="button"
              variant="outline"
              @click="preview.metadata.refetch()"
              >Повторить загрузку формул</Button
            ></AlertDescription
          ></Alert
        >
        <CalculationPreviewPanel
          v-if="
            fieldCanPreview(editor.selected.value) &&
            !fieldIsReadonly(editor.selected.value)
          "
          :field-kind="editor.selected.value.typeDefinition.kind"
          :locale="preview.locale.value"
          :locales="editor.metadata.data.value.locales"
          :products="preview.products.data.value?.items ?? []"
          :products-total="preview.products.data.value?.total ?? 0"
          :variants="preview.variants.data.value?.items ?? []"
          :variants-total="preview.variants.data.value?.total ?? 0"
          :search="preview.search.value"
          :offset="preview.offset.value"
          :variant-offset="preview.variantOffset.value"
          :root="preview.root.value"
          :variant="preview.variant.value"
          :loading="preview.products.isFetching.value"
          :variants-loading="preview.variants.isFetching.value"
          :source-error="
            sourceError
              ? 'Не удалось загрузить товары каталога. Повторите загрузку.'
              : ''
          "
          :error="previewError"
          :pending="preview.pending.value"
          :stale="preview.stale.value"
          :result="preview.result.value"
          :can-preview="preview.canPreview.value"
          :disabled="previewBlocked"
          @locale="preview.locale.value = $event"
          @search="preview.search.value = $event"
          @offset="preview.offset.value = $event"
          @variant-offset="preview.variantOffset.value = $event"
          @root="preview.root.value = $event"
          @variant="preview.variant.value = $event"
          @preview="preview.preview"
          @retry="retryPreviewSources"
        />
      </div>
    </div>
  </div>
</template>
