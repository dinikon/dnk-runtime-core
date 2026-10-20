<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { catalogItemLocation, invalidateCatalogItems } from "@/modules/catalog";
import { useTenantStore } from "@/app/stores/tenant";
import { useChannelsContext } from "../model/use-channels-context";
import { usePublicationImportQuery } from "../model/queries/use-publication-import-query";
import { usePublicationSnapshotQuery } from "../model/queries/use-publication-snapshot-query";
import { useConnectionReferencesQuery } from "../model/queries/use-references-query";
import { useStartPublicationImport } from "../model/mutations/use-start-publication-import";
import { useRetryPublicationImport } from "../model/mutations/use-retry-publication-import";
import { useCancelPublicationImport } from "../model/mutations/use-cancel-publication-import";
import { useCreateCatalogDraft } from "../model/mutations/use-create-catalog-draft";
import { usePublicationImportDraft } from "../model/use-publication-import-draft";
import { channelErrorMessage } from "../model/channels.errors";
import { ChannelsApiError } from "../api/channels.error";
import { dateLabel, reasonLabel } from "../model/channels.presentation";
import type { ImportDraftValues } from "../model/publication-import.types";
import type { CreateDraftInput } from "../model/catalog-links.types";
import PublicationImportForm from "../ui/PublicationImportForm.vue";
const route = useRoute(),
  router = useRouter(),
  ctx = useChannelsContext(),
  cache = useQueryClient(),
  tenant = useTenantStore();
const id = computed(() => String(route.params.preparationId ?? "")),
  publicationId = computed(() => String(route.params.publicationId ?? "")),
  channelId = computed(() => String(route.params.channelId ?? ""));
const initialized = ref(false),
  actionError = ref<string | null>(null);
const start = useStartPublicationImport(ctx),
  retry = useRetryPublicationImport(ctx),
  cancel = useCancelPublicationImport(ctx),
  create = useCreateCatalogDraft(ctx);
const query = usePublicationImportQuery(ctx, id, initialized),
  references = useConnectionReferencesQuery(ctx),
  source = usePublicationSnapshotQuery(ctx, publicationId);
const preparation = computed(() =>
  query.data.value?.id === id.value &&
  query.data.value.publicationId === publicationId.value
    ? query.data.value
    : undefined,
);
const draft = usePublicationImportDraft(ctx, id),
  { values, uncertain, dirty } = draft;
const pending = computed(
  () =>
    start.isPending.value ||
    retry.isPending.value ||
    cancel.isPending.value ||
    create.isPending.value,
);
const running = computed(() =>
  ["queued", "reading", "images"].includes(preparation.value?.status ?? ""),
);
const galleryErrors = computed(
  () => preparation.value?.images.some((image) => !!image.errorCode) ?? false,
);
const completed = computed(
  () =>
    preparation.value?.images.filter(
      (image) => image.previewUrl || image.errorCode,
    ).length ?? 0,
);
const progress = computed(() =>
  preparation.value?.status === "ready"
    ? 100
    : preparation.value?.status === "images"
      ? 20 +
        (80 * completed.value) / Math.max(1, preparation.value.images.length)
      : 5,
);
const canRetry = computed(
  () =>
    (preparation.value?.status === "error" &&
      preparation.value.errorCode !== "import_source_changed") ||
    (preparation.value?.status === "ready" && galleryErrors.value),
);
const canCreate = computed(
  () =>
    preparation.value?.status === "ready" && !running.value && !uncertain.value,
);
const activeLocale = computed(() =>
  values.value &&
  typeof route.query.locale === "string" &&
  route.query.locale in values.value.titles
    ? route.query.locale
    : (Object.keys(values.value?.titles ?? {})[0] ?? ""),
);
function setLocale(locale: string): void {
  void router.replace({ query: { ...route.query, locale } });
}
const labels: Record<string, string> = {
  queued: "Подготовка в очереди",
  reading: "Получаем тексты и галерею",
  images: "Переносим фотографии",
  ready: "Карточка готова к проверке",
  error: "Не удалось подготовить карточку",
  consumed: "Товар уже создан",
  cancelled: "Подготовка отменена",
  expired: "Срок подготовки истёк",
};
async function initialize(): Promise<void> {
  if (!ctx.enabled.value || !id.value) return;
  const validContext = ctx.capture(),
    identifier = id.value;
  actionError.value = null;
  const observedRevision = Number(route.query.revision);
  if (!Number.isInteger(observedRevision) || observedRevision < 1) {
    initialized.value = true;
    return;
  }
  try {
    await start.mutateAsync({
      publicationId: publicationId.value,
      preparationId: identifier,
      observedRevision,
    });
    if (validContext() && id.value === identifier) initialized.value = true;
  } catch (error: unknown) {
    if (validContext() && id.value === identifier)
      actionError.value = channelErrorMessage(error);
  }
}
watch(
  () => [ctx.scope.value, ctx.enabled.value, id.value],
  () => {
    initialized.value = false;
    actionError.value = null;
    void initialize();
  },
  { immediate: true },
);
watch(
  preparation,
  (value) => {
    if (value?.values) draft.hydrate(value);
  },
  { immediate: true },
);
function back(): void {
  void router.push({
    name: "channel-detail",
    params: { channelId: channelId.value },
    query: { tab: "publications" },
  });
}
async function retryImages(): Promise<void> {
  if (!preparation.value || pending.value || uncertain.value) return;
  const valid = ctx.capture(),
    identifier = id.value;
  actionError.value = null;
  try {
    await retry.mutateAsync({
      preparationId: identifier,
      revision: preparation.value.revision,
    });
  } catch (error: unknown) {
    if (valid() && id.value === identifier)
      actionError.value = channelErrorMessage(error);
  }
}
async function cancelPreparation(): Promise<void> {
  if (!preparation.value || pending.value || uncertain.value) return;
  if (
    !window.confirm(
      "Отменить подготовку? Временные фотографии будут освобождены.",
    )
  )
    return;
  const valid = ctx.capture(),
    identifier = id.value;
  try {
    await cancel.mutateAsync({
      preparationId: identifier,
      revision: preparation.value.revision,
    });
    if (valid() && id.value === identifier) {
      draft.clear();
      back();
    }
  } catch (error: unknown) {
    if (valid() && id.value === identifier)
      actionError.value = channelErrorMessage(error);
  }
}
async function restart(): Promise<void> {
  if (pending.value || uncertain.value) return;
  const valid = ctx.capture(),
    identifier = id.value;
  const fresh = await source.refetch();
  if (!valid() || id.value !== identifier) return;
  if (!fresh.data) {
    actionError.value = channelErrorMessage(fresh.error);
    return;
  }
  await router.push({
    name: "channel-publication-import",
    params: {
      channelId: channelId.value,
      publicationId: publicationId.value,
      preparationId: crypto.randomUUID(),
    },
    query: { revision: String(fresh.data.observedRevision) },
  });
}
async function submit(formValues?: ImportDraftValues): Promise<void> {
  if (
    pending.value ||
    (!uncertain.value && (!preparation.value || !formValues))
  )
    return;
  let input: CreateDraftInput;
  if (uncertain.value && draft.intent.value) input = draft.intent.value;
  else {
    if (!preparation.value || !formValues) return;
    input = {
      publicationId: publicationId.value,
      preparationId: id.value,
      preparationRevision: preparation.value.revision,
      observedRevision: preparation.value.observedRevision,
      requestKey: crypto.randomUUID(),
      values: formValues,
    };
    draft.submit(input);
  }
  const valid = ctx.capture(),
    identifier = id.value;
  actionError.value = null;
  try {
    const result = await create.mutateAsync(input);
    if (!valid() || id.value !== identifier) return;
    const locale = Object.keys(input.values.titles)[0] ?? "uk";
    draft.clear();
    if (tenant.tenant?.tenant_id)
      await invalidateCatalogItems(cache, tenant.tenant.tenant_id);
    if (!valid() || id.value !== identifier) return;
    toast.success("Draft создан, тексты и галерея перенесены");
    await router.push(catalogItemLocation(result.catalogItemId, locale));
  } catch (error: unknown) {
    if (!valid() || id.value !== identifier) return;
    if (
      error instanceof ChannelsApiError &&
      error.status !== undefined &&
      error.status < 500
    )
      draft.reject();
    actionError.value = channelErrorMessage(error);
  }
}
function canLeave(): boolean {
  return (
    !pending.value &&
    ((!dirty.value && !uncertain.value) ||
      window.confirm(
        uncertain.value
          ? "Результат создания ещё не подтверждён. Запрос сохранён: вернитесь по этой ссылке, чтобы проверить его без дубликата."
          : "Выйти из предпросмотра? Введённые значения сохранены в этой вкладке браузера.",
      ))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) =>
  to.params.preparationId === from.params.preparationId ? true : canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (dirty.value || pending.value || uncertain.value) event.preventDefault();
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnload));
</script>
<template>
  <div
    class="mx-auto flex min-h-0 w-full max-w-5xl min-w-0 flex-1 flex-col gap-6 overflow-y-auto p-4 md:p-6"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <Button variant="ghost" :disabled="pending" @click="back"
        ><ArrowLeft data-icon="inline-start" />К публикациям</Button
      ><Badge variant="secondary">Новый товар · Draft</Badge>
    </div>
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">
        Создать товар из публикации
      </h1>
      <p class="mt-2 text-sm text-muted-foreground">
        Проверьте тексты, фотографии, цену и наличие. После создания товар
        станет самостоятельной карточкой каталога.
      </p>
    </div>
    <Alert v-if="actionError || query.error.value" variant="destructive"
      ><AlertTitle>Действие не завершено</AlertTitle
      ><AlertDescription>{{
        actionError ?? channelErrorMessage(query.error.value)
      }}</AlertDescription></Alert
    >
    <Alert v-if="uncertain"
      ><AlertTitle>Проверяем результат создания</AlertTitle
      ><AlertDescription
        >Ответ сервера пока не подтверждён. Повтор отправит сохранённый запрос с
        теми же текстами и фотографиями.</AlertDescription
      ><Button
        type="button"
        class="mt-3"
        :disabled="pending"
        @click="submit()"
        >{{
          pending ? "Проверяем…" : "Проверить результат без дубликата"
        }}</Button
      ></Alert
    >
    <div
      v-if="!preparation && (start.isPending.value || query.isLoading.value)"
      class="flex flex-col gap-4"
      aria-label="Подготовка карточки"
    >
      <Skeleton class="h-28 w-full" /><Skeleton class="h-64 w-full" />
    </div>
    <Card v-if="preparation"
      ><CardHeader
        ><CardTitle aria-live="polite">{{
          labels[preparation.status] ?? preparation.status
        }}</CardTitle
        ><CardDescription>{{
          running
            ? "Можно оставить эту страницу открытой или вернуться к ней позже по той же ссылке."
            : "Предпросмотр действителен 24 часа. Синхронизация остаётся выключенной."
        }}</CardDescription></CardHeader
      ><CardContent class="flex flex-col gap-3">
        <p v-if="preparation.readAt" class="text-sm text-muted-foreground">
          Данные получены: {{ dateLabel(preparation.readAt) }}
        </p>
        <template v-if="running"
          ><Progress :model-value="progress" />
          <p class="text-sm text-muted-foreground">
            {{
              preparation.status === "images"
                ? `Обработано фотографий: ${completed} из ${preparation.images.length}`
                : "Получаем полное содержимое публикации…"
            }}
          </p></template
        >
        <Alert v-if="preparation.errorCode"
          ><AlertDescription>{{
            reasonLabel(preparation.errorCode)
          }}</AlertDescription></Alert
        >
        <Alert v-if="galleryErrors"
          ><AlertTitle>Часть фотографий не перенесена</AlertTitle
          ><AlertDescription
            >Повторите перенос или исключите неготовые фотографии из галереи.
            Уже загруженные файлы сохранятся.</AlertDescription
          ></Alert
        >
        <ul
          v-if="preparation.warnings.length"
          class="list-inside list-disc text-sm text-muted-foreground"
        >
          <li v-for="warning in preparation.warnings" :key="warning">
            {{ reasonLabel(warning) }}
          </li>
        </ul>
        <div class="flex flex-wrap gap-2">
          <Button
            v-if="canRetry"
            variant="outline"
            :disabled="pending || uncertain"
            @click="retryImages"
            >Повторить загрузку</Button
          ><Button
            v-if="!running && preparation.status !== 'consumed'"
            variant="outline"
            :disabled="pending || uncertain"
            @click="restart"
            >Получить карточку заново</Button
          ><Button
            v-if="
              !['consumed', 'expired', 'cancelled'].includes(preparation.status)
            "
            variant="ghost"
            :disabled="pending || uncertain"
            @click="cancelPreparation"
            >Отменить подготовку</Button
          >
        </div>
      </CardContent></Card
    >
    <Button
      v-if="!preparation && !pending"
      variant="outline"
      @click="initialized ? query.refetch() : initialize()"
      >Повторить получение</Button
    >
    <PublicationImportForm
      v-if="
        values &&
        preparation &&
        (['ready', 'images'].includes(preparation.status) || uncertain)
      "
      :key="id"
      :locale="activeLocale"
      :values="values"
      :images="preparation.images"
      :references="references.data.value"
      :disabled="pending || !canCreate"
      :pending="create.isPending.value"
      @update:values="(value) => (values = value)"
      @locale="setLocale"
      @submit="submit"
    />
    <Alert v-if="preparation?.status === 'consumed' && !uncertain"
      ><AlertDescription
        >Товар уже создан и связан с публикацией. Откройте его из списка
        публикаций.</AlertDescription
      ></Alert
    >
  </div>
</template>
