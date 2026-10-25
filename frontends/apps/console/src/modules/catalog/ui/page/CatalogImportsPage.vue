<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { getApiErrorMessage } from "@/app/providers/http";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogFooter from "../CatalogFooter.vue";
import CatalogImportWizardDialog from "../import/CatalogImportWizardDialog.vue";
import CatalogImportsList from "../import/CatalogImportsList.vue";
import { useImportsPageState } from "../../model/use-imports-page-state";
import {
  useCatalogImportsQuery,
  useCatalogImportQuery,
  useCatalogImportRowsQuery,
} from "../../model/import.queries";
import {
  useCreateCatalogImport,
  useConfigureCatalogImport,
  useStartCatalogImport,
  useResumeCatalogImport,
  useCancelCatalogImport,
  useDownloadImportReport,
} from "../../model/import.mutations";
import {
  cloneImportConfiguration,
  importConfigurationEquals,
  acknowledgeImportConfiguration,
} from "../../model/import.draft";
import { importKeys } from "../../model/import.query-keys";
import type { ImportConfiguration } from "../../model/import.types";
const state = useImportsPageState(),
  tenant = useTenantStore(),
  user = useUserStore(),
  cache = useQueryClient();
const tenantId = computed(() => tenant.tenant?.tenant_id ?? ""),
  session = computed(() => `${tenantId.value}:${user.user?.id ?? ""}`);
const runs = useCatalogImportsQuery(tenantId, session, state.page),
  detail = useCatalogImportQuery(tenantId, session, state.id);
const showRows = computed(
  () =>
    !!detail.data.value &&
    !["preparing", "mapping"].includes(detail.data.value.run.status),
);
const rows = useCatalogImportRowsQuery(
  tenantId,
  session,
  state.id,
  state.rowPage,
  state.outcome,
  showRows,
);
const creation = useCreateCatalogImport(tenantId, session),
  configuration = useConfigureCatalogImport(tenantId, session),
  start = useStartCatalogImport(tenantId, session),
  resume = useResumeCatalogImport(tenantId, session),
  cancel = useCancelCatalogImport(tenantId, session),
  report = useDownloadImportReport();
const draft = ref<ImportConfiguration | null>(null),
  draftId = ref(""),
  draftVersion = ref(0),
  sourceKey = ref(crypto.randomUUID()),
  actionError = ref("");
const acknowledged = ref<ImportConfiguration | null>(null),
  submitted = ref<ImportConfiguration | null>(null);
const dirty = computed(
  () =>
    !!draft.value &&
    !!detail.data.value &&
    !importConfigurationEquals(draft.value, detail.data.value.configuration),
);
const pending = computed(
  () =>
    configuration.isPending.value ||
    start.isPending.value ||
    resume.isPending.value ||
    cancel.isPending.value ||
    report.isPending.value,
);
let mounted = true;
onBeforeUnmount(() => {
  mounted = false;
});
function capture(): () => boolean {
  const value = session.value,
    path = state.route.fullPath;
  return () =>
    mounted && value === session.value && path === state.route.fullPath;
}
watch(
  () => detail.data.value,
  (value) => {
    if (!value) return;
    if (
      draftId.value !== value.run.id ||
      !draft.value ||
      (value.run.status === "mapping" &&
        value.run.version !== draftVersion.value)
    ) {
      draft.value =
        draft.value && acknowledged.value && draftId.value === value.run.id
          ? acknowledgeImportConfiguration(
              draft.value,
              acknowledged.value,
              submitted.value,
              value.configuration,
            )
          : cloneImportConfiguration(value.configuration);
      acknowledged.value = cloneImportConfiguration(value.configuration);
      if (value.run.status === "mapping") submitted.value = null;
      draftId.value = value.run.id;
      if (value.run.status === "mapping")
        draftVersion.value = value.run.version;
    }
  },
);
watch(
  () => [
    detail.data.value?.run.id,
    detail.data.value?.run.processed,
    detail.data.value?.run.status,
  ],
  () => {
    if (!detail.data.value) return;
    void cache.invalidateQueries({ queryKey: ["catalog", tenantId.value] });
    void cache.invalidateQueries({
      queryKey: [...importKeys.all(tenantId.value, session.value), "list"],
    });
    void cache.invalidateQueries({
      queryKey: [...importKeys.all(tenantId.value, session.value), "rows"],
    });
  },
);
watch(
  () => [tenantId.value, session.value],
  (_next, previous) => {
    if (!previous[0]) return;
    if (previous[0]) {
      void cache.cancelQueries({
        queryKey: importKeys.all(previous[0]!, previous[1]!),
      });
      cache.removeQueries({
        queryKey: importKeys.all(previous[0]!, previous[1]!),
      });
    }
    draft.value = null;
    acknowledged.value = submitted.value = null;
    draftId.value = "";
    draftVersion.value = 0;
    actionError.value = "";
    sourceKey.value = crypto.randomUUID();
    if (state.open.value) state.close();
  },
);
watch(
  () => state.open.value,
  (value) => {
    if (!value) {
      sourceKey.value = crypto.randomUUID();
      actionError.value = "";
      draft.value = null;
      acknowledged.value = submitted.value = null;
      draftId.value = "";
    }
  },
);
async function create(source: {
  file: File | null;
  url: string;
}): Promise<void> {
  if (creation.isPending.value) return;
  const valid = capture();
  actionError.value = "";
  try {
    const result = await creation.mutateAsync({
      ...source,
      key: sourceKey.value,
      defaultLocale: String(
        state.route.query.locale || user.user?.interface_language || "uk",
      ),
      timezone: user.user?.timezone || "Europe/Kyiv",
    });
    if (valid()) state.show(result.id);
  } catch (error) {
    if (valid())
      actionError.value = getApiErrorMessage(
        error,
        "Не удалось загрузить источник. Повтор использует тот же ключ и не создаст дубликат.",
      );
  }
}
async function preview(): Promise<void> {
  if (!draft.value || pending.value) return;
  const valid = capture();
  actionError.value = "";
  try {
    submitted.value = cloneImportConfiguration(draft.value);
    await configuration.mutateAsync({
      id: state.id.value,
      configuration: cloneImportConfiguration(draft.value),
    });
  } catch (error) {
    if (valid()) {
      submitted.value = null;
      actionError.value = getApiErrorMessage(
        error,
        "Не удалось обновить предпросмотр.",
      );
    }
  }
}
async function run(): Promise<void> {
  if (!detail.data.value || dirty.value || pending.value) return;
  const valid = capture();
  actionError.value = "";
  try {
    await start.mutateAsync({
      id: state.id.value,
      version: detail.data.value.run.version,
    });
  } catch (error) {
    if (valid()) {
      actionError.value = getApiErrorMessage(
        error,
        "Не удалось запустить импорт. Обновите состояние и повторите запуск.",
      );
      void detail.refetch();
    }
  }
}
async function continueImport(): Promise<void> {
  if (!detail.data.value?.run.canResume || pending.value) return;
  const valid = capture(),
    generation = detail.data.value.run.generation;
  actionError.value = "";
  try {
    await resume.mutateAsync({ id: state.id.value, generation });
  } catch (error) {
    if (!valid()) return;
    const refreshed = await detail.refetch();
    if (!valid()) return;
    if (refreshed.data && refreshed.data.run.generation > generation) return;
    actionError.value = getApiErrorMessage(
      error,
      "Не удалось продолжить импорт. Повторите действие после обновления состояния.",
    );
  }
}
async function stop(): Promise<void> {
  const valid = capture();
  actionError.value = "";
  try {
    await cancel.mutateAsync(state.id.value);
  } catch (error) {
    if (valid())
      actionError.value = getApiErrorMessage(
        error,
        "Не удалось остановить импорт.",
      );
  }
}
async function download(): Promise<void> {
  const valid = capture(),
    id = state.id.value;
  actionError.value = "";
  try {
    const blob = await report.mutateAsync(id);
    if (!valid()) return;
    const url = URL.createObjectURL(blob),
      link = document.createElement("a");
    link.href = url;
    link.download = `catalog-import-${id}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    if (valid())
      actionError.value = getApiErrorMessage(
        error,
        "Не удалось скачать отчёт.",
      );
  }
}
const detailError = computed(
  () =>
    actionError.value ||
    (detail.isError.value
      ? getApiErrorMessage(detail.error.value, "Не удалось загрузить импорт.")
      : ""),
);
const rowsError = computed(() =>
  rows.isError.value
    ? getApiErrorMessage(rows.error.value, "Не удалось загрузить результаты.")
    : "",
);
</script>
<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto p-4 sm:p-6"
  >
    <CatalogHeader
      title="Импорт товаров"
      description="Загрузки из файлов и ссылок, прогресс и результаты"
      action="Импортировать позиции"
      :disabled="!tenantId"
      @create="state.show()"
    />
    <div>
      <Button variant="ghost" @click="state.router.push('/catalog/items')"
        >← К товарам</Button
      >
    </div>
    <Alert v-if="runs.isError.value" variant="destructive"
      ><AlertTitle>Журнал недоступен</AlertTitle
      ><AlertDescription
        >{{
          getApiErrorMessage(runs.error.value, "Не удалось загрузить журнал.")
        }}<Button variant="outline" size="sm" @click="runs.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Skeleton v-else-if="runs.isPending.value" class="h-64 w-full" />
    <CatalogImportsList
      v-else-if="runs.data.value?.items.length"
      :items="runs.data.value.items"
      @open="state.show"
    />
    <Empty v-else class="border border-dashed"
      ><EmptyHeader
        ><EmptyTitle>Импортов пока нет</EmptyTitle
        ><EmptyDescription
          >Прикрепите CSV/XML или укажите ссылку, чтобы перенести
          товары.</EmptyDescription
        ></EmptyHeader
      ><EmptyContent
        ><Button variant="outline" @click="state.show()"
          >Первый импорт</Button
        ></EmptyContent
      ></Empty
    >
    <CatalogFooter
      :page="state.page.value"
      :total="runs.data.value?.total ?? 0"
      :page-size="20"
      @page="(value) => state.query({ page: value })"
    />
    <CatalogImportWizardDialog
      :open="state.open.value"
      :existing="!!state.id.value"
      :detail="state.id.value ? detail.data.value : undefined"
      :draft="draft"
      :dirty="dirty"
      :loading="!!state.id.value && detail.isPending.value"
      :pending="pending"
      :source-pending="creation.isPending.value"
      :error="detailError"
      :rows="rows.data.value"
      :rows-loading="rows.isPending.value"
      :rows-error="rowsError"
      :row-page="state.rowPage.value"
      :outcome="state.outcome.value"
      @close="state.close"
      @retry="detail.refetch()"
      @source="create"
      @change="
        (value) => {
          draft = value;
        }
      "
      @preview="preview"
      @start="run"
      @cancel="stop"
      @resume="continueImport"
      @report="download"
      @row-page="(value) => state.query({ row_page: value })"
      @outcome="
        (value) =>
          state.query({ result: value || undefined, row_page: undefined })
      "
      @rows-retry="rows.refetch()"
      @item="
        (id) =>
          state.router.push({
            path: `/catalog/items/${id}`,
            query: { locale: draft?.defaultLocale || 'uk' },
          })
      "
    />
  </div>
</template>
