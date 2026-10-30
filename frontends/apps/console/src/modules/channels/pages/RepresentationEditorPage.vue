<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import { useContentDeliveries } from "../model/use-content-deliveries";
import { useRequestContentDelivery } from "../model/use-request-content-delivery";
import { useReconcileContentDelivery } from "../model/use-reconcile-content-delivery";
import {
  contentDeliveryError,
  contentDeliveryIssue,
} from "../model/content-delivery.errors";
import type { ContentDelivery } from "../model/content-delivery.types";
import ContentDeliveriesPanel from "../ui/bindings/ContentDeliveriesPanel.vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useImageFilesQuery, type FilesFilters } from "@/modules/files";
import { useChannelScope } from "../model/use-channel-scope";
import {
  useRepresentationDetails,
  useRepresentationPreview,
} from "../model/representation.queries";
import { useSaveRepresentation } from "../model/use-save-representation";
import { useEnableRepresentationExport } from "../model/use-enable-representation-export";
import { useDisableRepresentationExport } from "../model/use-disable-representation-export";
import { useChannelEditorNavigation } from "../model/use-channel-editor-navigation";
import {
  normalizeRepresentationOverrides,
  representationDraftKey,
  representationVersion,
} from "../model/representation.draft";
import {
  representationErrorMessage,
  representationIssueMessage,
} from "../model/representation.errors";
import type {
  RepresentationDetails,
  RepresentationOverrides,
  RepresentationVersion,
  RepresentationDraftInput,
  LocalizedOverrides,
} from "../model/representation.types";
import type { CatalogBinding } from "../model/bindings/binding.types";
import RepresentationOverridesForm from "../ui/bindings/RepresentationOverridesForm.vue";
import RepresentationPreviewPanel from "../ui/bindings/RepresentationPreviewPanel.vue";
import RepresentationImagePicker from "../ui/bindings/RepresentationImagePicker.vue";

const props = defineProps<{ group: CatalogBinding; locale: string }>();
const emit = defineEmits<{ state: [dirty: boolean, busy: boolean] }>();
const scope = useChannelScope();
const channelId = computed(() => props.group.channelId),
  groupId = computed(() => props.group.id);
const detail = useRepresentationDetails(channelId, groupId),
  savedPreview = useRepresentationPreview(channelId, groupId);
const save = useSaveRepresentation(),
  enable = useEnableRepresentationExport(),
  disable = useDisableRepresentationExport();
const outgoing = useRequestContentDelivery(),
  reconcileDelivery = useReconcileContentDelivery();
const deliveryEnabled = computed(
  () => savedPreview.data.value?.platform === "woocommerce",
);
const deliveries = useContentDeliveries(channelId, groupId, deliveryEnabled);
const reviewedFingerprint = ref("");
const draft = ref<RepresentationOverrides | null>(null),
  version = ref<RepresentationVersion | null>(null),
  baseline = ref("");
const requestedPreview = ref<RepresentationDraftInput | null>(null);
const draftPreview = useRepresentationPreview(
  channelId,
  groupId,
  requestedPreview,
);
const locale = ref(props.locale),
  selection = ref("common"),
  actionError = ref("");
const busy = computed(
  () =>
    save.isPending.value ||
    enable.isPending.value ||
    disable.isPending.value ||
    outgoing.isPending.value ||
    reconcileDelivery.isPending.value,
);
const flagsBusy = computed(
  () => enable.isPending.value || disable.isPending.value,
);
const dirty = computed(
  () => !!draft.value && representationDraftKey(draft.value) !== baseline.value,
);
let active = true;
watch([dirty, busy], ([changed, pending]) => emit("state", changed, pending), {
  immediate: true,
});
onBeforeUnmount(() => {
  active = false;
  emit("state", false, false);
});
useChannelEditorNavigation(
  dirty,
  busy,
  "Изменения представления не сохранены. Покинуть страницу?",
);

function load(value: RepresentationDetails): void {
  draft.value = normalizeRepresentationOverrides(value.state.overrides);
  baseline.value = representationDraftKey(value.state.overrides);
  version.value = representationVersion(value);
  requestedPreview.value = null;
  if (
    selection.value !== "common" &&
    !value.items.some((item) => item.id === selection.value)
  )
    selection.value = "common";
  if (!locales.value.includes(locale.value))
    locale.value = value.locales[0] ?? "";
}
const locales = computed(() => [
  ...new Set([
    ...(detail.data.value?.locales ?? []),
    ...Object.keys(draft.value?.common ?? {}),
    ...Object.values(draft.value?.items ?? {}).flatMap((localized) =>
      Object.keys(localized),
    ),
  ]),
]);
watch(
  () => detail.data.value,
  (value) => {
    if (value && (!draft.value || (!dirty.value && !busy.value))) load(value);
  },
  { immediate: true },
);
const inactive = computed(
  () => !detail.data.value?.locales.includes(locale.value),
);
const stale = computed(
  () =>
    !!version.value &&
    !!detail.data.value &&
    (version.value.expectedRevision !== detail.data.value.state.revision ||
      version.value.expectedBindingRevision !==
        detail.data.value.bindingRevision ||
      version.value.expectedConfigRevision !==
        detail.data.value.configRevision),
);
const fields = computed<LocalizedOverrides>(() =>
  selection.value === "common"
    ? (draft.value?.common[locale.value] ?? {})
    : (draft.value?.items[selection.value]?.[locale.value] ?? {}),
);
const preview = computed(() =>
  requestedPreview.value ? draftPreview.data.value : savedPreview.data.value,
);
const previewLoading = computed(() =>
  requestedPreview.value
    ? draftPreview.isFetching.value
    : savedPreview.isFetching.value,
);
const previewError = computed(() =>
  requestedPreview.value ? draftPreview.error.value : savedPreview.error.value,
);
const previewStale = computed(
  () =>
    dirty.value &&
    (!requestedPreview.value ||
      representationDraftKey(requestedPreview.value.overrides) !==
        representationDraftKey(draft.value!)),
);
const inherited = computed(() => {
  const target =
    selection.value === "common"
      ? savedPreview.data.value?.targets[0]
      : savedPreview.data.value?.targets.find(
          (target) => target.bindingItemId === selection.value,
        );
  const catalog = target?.catalogContent.find(
    (content) => content.locale === locale.value,
  );
  if (!catalog || selection.value === "common") return catalog;
  const common = draft.value?.common[locale.value];
  return {
    ...catalog,
    title: common?.title ?? catalog.title,
    body: common?.body ?? catalog.body,
    gallery: common?.gallery ?? catalog.gallery,
  };
});
function updateFields(value: LocalizedOverrides): void {
  if (!draft.value) return;
  const next = normalizeRepresentationOverrides(draft.value);
  if (selection.value === "common") next.common[locale.value] = value;
  else
    next.items[selection.value] = {
      ...next.items[selection.value],
      [locale.value]: value,
    };
  draft.value = normalizeRepresentationOverrides(next);
  actionError.value = "";
}
function contextKey(): string {
  return JSON.stringify([scope.value, channelId.value, groupId.value]);
}
async function persist(): Promise<void> {
  if (!draft.value || !version.value || busy.value) return;
  const captured = contextKey(),
    submitted = normalizeRepresentationOverrides(draft.value),
    submittedKey = representationDraftKey(submitted);
  actionError.value = "";
  try {
    const result = await save.mutateAsync({
      channelId: channelId.value,
      groupId: groupId.value,
      ...version.value,
      overrides: submitted,
    });
    if (!active || captured !== contextKey()) return;
    version.value = representationVersion(result);
    baseline.value = representationDraftKey(result.state.overrides);
    if (representationDraftKey(draft.value) === submittedKey)
      draft.value = normalizeRepresentationOverrides(result.state.overrides);
    requestedPreview.value = null;
  } catch (error) {
    if (active && captured === contextKey())
      actionError.value = representationErrorMessage(error);
  }
}
async function changePermission(allowed: boolean): Promise<void> {
  if (!version.value || busy.value || (allowed && dirty.value)) return;
  const captured = contextKey();
  actionError.value = "";
  try {
    const input = {
      channelId: channelId.value,
      groupId: groupId.value,
      ...version.value,
    };
    const result = await (allowed
      ? enable.mutateAsync(input)
      : disable.mutateAsync(input));
    if (!active || captured !== contextKey()) return;
    version.value = representationVersion(result);
    baseline.value = representationDraftKey(result.state.overrides);
  } catch (error) {
    if (active && captured === contextKey())
      actionError.value = representationErrorMessage(error);
  }
}
async function checkDraft(): Promise<void> {
  if (!draft.value || !version.value || busy.value) return;
  const input = {
    ...version.value,
    overrides: normalizeRepresentationOverrides(draft.value),
  };
  if (JSON.stringify(requestedPreview.value) === JSON.stringify(input))
    await draftPreview.refetch();
  else requestedPreview.value = input;
}
async function reload(): Promise<void> {
  if (
    busy.value ||
    (dirty.value &&
      !window.confirm(
        "Перечитать представление и сбросить несохранённые изменения?",
      ))
  )
    return;
  const previousDraft = draft.value && representationDraftKey(draft.value);
  const result = await detail.refetch();
  if (
    result.isSuccess &&
    result.data &&
    active &&
    (!previousDraft ||
      (draft.value && representationDraftKey(draft.value) === previousDraft))
  ) {
    load(result.data);
    actionError.value = "";
  }
}
const pickerOpen = ref(false),
  fileSearch = ref(""),
  filePage = ref(1);
const fileFilters = computed<FilesFilters>(() => ({
  search: fileSearch.value,
  bucket_ids: [],
  category: "images",
  page: filePage.value,
  page_size: 25,
}));
const files = useImageFilesQuery(fileFilters, pickerOpen);
const imageChoices = computed(() => {
  const choices = new Map<string, { fileId: string; name: string }>();
  for (const target of savedPreview.data.value?.targets ?? [])
    for (const content of target.catalogContent)
      for (const image of content.gallery ?? []) {
        const name = image.alt || image.caption || "Изображение Catalog";
        if (
          !fileSearch.value ||
          name.toLowerCase().includes(fileSearch.value.toLowerCase())
        )
          choices.set(image.fileId, { fileId: image.fileId, name });
      }
  for (const file of files.data.value?.items ?? [])
    choices.set(file.file_id, { fileId: file.file_id, name: file.name });
  return [...choices.values()].filter(
    (image) =>
      !fields.value.gallery?.some(
        (selected) => selected.fileId === image.fileId,
      ),
  );
});
function pickImage(fileId: string): void {
  updateFields({
    ...fields.value,
    gallery: [
      ...(fields.value.gallery ?? []),
      { fileId, alt: "", caption: "" },
    ],
  });
  pickerOpen.value = false;
}
const canReview = computed(
  () =>
    !dirty.value &&
    !stale.value &&
    !previewLoading.value &&
    !savedPreview.error.value &&
    !!savedPreview.data.value?.contentFingerprint,
);
const canDeliver = computed(
  () =>
    canReview.value &&
    detail.data.value?.state.exportEnabled === true &&
    reviewedFingerprint.value === savedPreview.data.value?.contentFingerprint &&
    !savedPreview.data.value?.deliveryIssues.length &&
    !savedPreview.data.value?.exportBlockers.length &&
    !deliveries.data.value?.some(
      (item) =>
        item.status === "unknown" ||
        (item.status === "in_flight" && item.recoveryRequired) ||
        (!item.recoveryRequired &&
          ["queued", "in_flight"].includes(item.status) &&
          item.contentFingerprint === reviewedFingerprint.value),
    ),
);
const deliveryErrors = computed(() =>
  Object.fromEntries(
    (deliveries.data.value ?? []).map((item) => [
      item.publicationId,
      item.errorCode ? contentDeliveryIssue(item.errorCode) : "",
    ]),
  ),
);
watch([() => savedPreview.data.value?.contentFingerprint, contextKey], () => {
  reviewedFingerprint.value = "";
});
async function deliver(): Promise<void> {
  if (!canDeliver.value || !version.value || busy.value) return;
  const captured = contextKey();
  actionError.value = "";
  try {
    await outgoing.mutateAsync({
      channelId: channelId.value,
      groupId: groupId.value,
      ...version.value,
      contentFingerprint: reviewedFingerprint.value,
    });
  } catch (error) {
    if (active && captured === contextKey()) {
      actionError.value = contentDeliveryError(error);
      reviewedFingerprint.value = "";
      await Promise.allSettled([deliveries.refetch(), savedPreview.refetch()]);
    }
  }
}
async function reconcile(item: ContentDelivery): Promise<void> {
  if (busy.value) return;
  const captured = contextKey();
  actionError.value = "";
  try {
    await reconcileDelivery.mutateAsync({
      channelId: channelId.value,
      groupId: groupId.value,
      publicationId: item.publicationId,
      expectedRevision: item.revision,
    });
  } catch (error) {
    if (active && captured === contextKey())
      actionError.value = contentDeliveryError(error);
  }
}
const canEnable = computed(
  () =>
    !!detail.data.value?.state.id &&
    !dirty.value &&
    !busy.value &&
    !stale.value &&
    !savedPreview.isFetching.value &&
    !savedPreview.error.value &&
    !!savedPreview.data.value &&
    !savedPreview.data.value.exportBlockers.length,
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row">
      <section class="min-w-0 flex-1 space-y-5 p-4 lg:border-r">
        <Alert v-if="detail.error.value" variant="destructive"
          ><AlertDescription
            >{{ representationErrorMessage(detail.error.value) }}
            <Button type="button" variant="outline" @click="reload"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <Skeleton v-if="detail.isPending.value && !draft" class="h-64 w-full" />
        <template v-if="draft && detail.data.value">
          <div class="flex flex-wrap gap-3">
            <label class="min-w-0 flex-1 space-y-1 text-sm font-medium"
              >Область переопределения<select
                v-model="selection"
                aria-label="Область переопределения"
                class="block h-9 w-full rounded-md border border-input bg-background px-2"
              >
                <option value="common">Вся группа</option>
                <option
                  v-for="item in detail.data.value.items"
                  :key="item.id"
                  :value="item.id"
                >
                  Позиция
                  {{
                    savedPreview.data.value?.targets.find(
                      (target) => target.bindingItemId === item.id,
                    )?.externalId ?? "площадки"
                  }}
                </option>
              </select></label
            ><label class="space-y-1 text-sm font-medium"
              >Язык<select
                v-model="locale"
                aria-label="Язык переопределений"
                class="block h-9 rounded-md border border-input bg-background px-3"
              >
                <option v-for="code in locales" :key="code" :value="code">
                  {{ code }}
                </option>
              </select></label
            >
          </div>
          <p class="text-sm text-muted-foreground">
            {{
              selection === "common"
                ? "Общие значения применяются ко всем целям группы. Переопределения конкретной позиции имеют приоритет."
                : "Снятие переопределения возвращает общее значение группы или Catalog."
            }}
          </p>
          <Alert v-if="stale"
            ><AlertDescription
              >Контекст изменился после открытия редактора. Черновик сохранён в
              форме; перечитайте данные перед сохранением.</AlertDescription
            ></Alert
          >
          <RepresentationOverridesForm
            :value="fields"
            :inherited="inherited"
            :disabled="flagsBusy"
            :inactive="inactive"
            @update="updateFields"
            @pick-images="pickerOpen = true"
          />
          <div class="space-y-2 border-t pt-4">
            <p class="text-sm font-medium">
              {{
                detail.data.value.state.exportEnabled
                  ? "Экспорт контента разрешён"
                  : "Экспорт контента выключен"
              }}
            </p>
            <p class="text-sm text-muted-foreground">
              Разрешение сохраняется отдельно. Изменение состава группы
              выключает его до повторной проверки.
            </p>
            <ul
              v-if="savedPreview.data.value?.exportBlockers.length"
              class="space-y-1 text-sm text-muted-foreground"
            >
              <li
                v-for="code in savedPreview.data.value.exportBlockers"
                :key="code"
              >
                {{ representationIssueMessage(code) }}
              </li>
            </ul>
            <Button
              v-if="detail.data.value.state.exportEnabled"
              type="button"
              variant="outline"
              :disabled="busy"
              @click="changePermission(false)"
              >Выключить экспорт</Button
            ><Button
              v-else
              type="button"
              variant="outline"
              :disabled="!canEnable"
              @click="changePermission(true)"
              >Разрешить экспорт</Button
            >
            <p
              v-if="!detail.data.value.state.id"
              class="text-xs text-muted-foreground"
            >
              Для включения экспорта сначала сохраните представление.
            </p>
          </div>
          <ContentDeliveriesPanel
            v-if="deliveryEnabled"
            :items="deliveries.data.value ?? []"
            :loading="deliveries.isFetching.value"
            :error="
              deliveries.error.value
                ? contentDeliveryError(deliveries.error.value)
                : ''
            "
            :busy="busy"
            :can-request="canDeliver"
            :can-review="canReview"
            :reviewed="
              !!reviewedFingerprint &&
              reviewedFingerprint ===
                savedPreview.data.value?.contentFingerprint
            "
            :fingerprint="savedPreview.data.value?.contentFingerprint ?? ''"
            :issues="
              (savedPreview.data.value?.deliveryIssues ?? []).map((issue) =>
                contentDeliveryIssue(issue.code),
              )
            "
            :error-messages="deliveryErrors"
            @review="
              reviewedFingerprint = $event
                ? (savedPreview.data.value?.contentFingerprint ?? '')
                : ''
            "
            @request="deliver"
            @reconcile="reconcile"
            @refresh="deliveries.refetch()"
          />
        </template>
      </section>
      <section class="flex min-h-[300px] min-w-0 flex-1 flex-col lg:min-h-0">
        <p v-if="previewStale" class="px-4 pt-4 text-sm text-muted-foreground">
          Есть непроверенные изменения. Нажмите «Проверить черновик».
        </p>
        <RepresentationPreviewPanel
          :preview="preview"
          :locale="locale"
          :loading="previewLoading"
          :error="previewError ? representationErrorMessage(previewError) : ''"
          @retry="
            requestedPreview ? draftPreview.refetch() : savedPreview.refetch()
          "
        />
      </section>
    </div>
    <footer class="shrink-0 space-y-3 border-t p-4">
      <Alert v-if="actionError" variant="destructive"
        ><AlertDescription>{{ actionError }}</AlertDescription></Alert
      >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-sm text-muted-foreground">{{
          dirty
            ? "Есть несохранённые изменения"
            : detail.data.value?.state.id
              ? "Изменения сохранены"
              : "Представление ещё не сохранено"
        }}</span>
        <div class="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="busy"
            @click="reload"
            >Перечитать</Button
          ><Button
            type="button"
            variant="outline"
            :disabled="busy || !draft || previewLoading"
            @click="checkDraft"
            >Проверить черновик</Button
          ><Button
            type="button"
            :disabled="
              busy || !draft || (!dirty && !!detail.data.value?.state.id)
            "
            @click="persist"
            >{{
              save.isPending.value ? "Сохраняем…" : "Сохранить представление"
            }}</Button
          >
        </div>
      </div>
    </footer>
    <RepresentationImagePicker
      :open="pickerOpen"
      :items="imageChoices"
      :loading="files.isFetching.value"
      :error="
        files.error.value
          ? 'Не удалось получить список Files. Изображения Catalog можно выбрать, если они доступны ниже.'
          : ''
      "
      :search="fileSearch"
      :page="filePage"
      :total="files.data.value?.total ?? 0"
      @close="pickerOpen = false"
      @search="
        fileSearch = $event;
        filePage = 1;
      "
      @page="filePage = $event"
      @pick="pickImage"
      @retry="files.refetch()"
    />
  </div>
</template>
