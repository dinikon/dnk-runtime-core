<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { priceListsApi } from "../api/client";
import type { MappingConfig, PreviewResult, SourceFormat } from "../api/contracts";
import { priceListKeys } from "../model/query-keys";
import PriceListMappingStep from "../ui/forms/PriceListMappingStep.vue";
import PriceListScheduleStep from "../ui/forms/PriceListScheduleStep.vue";
import PriceListSourceStep from "../ui/forms/PriceListSourceStep.vue";

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const editMode = computed(() => route.name === "price-list-edit");
const priceListId = ref(editMode.value ? String(route.params.id) : "");
const step = ref(1);
const busy = ref(false);
const loading = ref(editMode.value);
const error = ref("");
const blockedStatus = ref<"active" | "archived" | "">("");
const sourceUrlDisplay = ref("");
const preview = ref<PreviewResult | null>(null);
const title = ref("");
const sourceUrl = ref("");
const sourceFormat = ref<SourceFormat>("xml");
const preset = ref<"prom_xml" | "custom">("custom");
const itemPath = ref("");
const sheetName = ref("Sheet1");
const headerRow = ref(1);
const mapping = ref<MappingConfig>({});
const cronExpression = ref("0 */6 * * *");
const timezone = ref("Europe/Kyiv");
const newItemPolicy = ref<"create" | "quarantine" | "ignore">("create");
const missingPolicy = ref<"mark_out_of_stock" | "mark_missing" | "archive" | "keep_last">("mark_out_of_stock");
const missingThreshold = ref(2);
const nextRuns = ref<string[]>([]);
const scheduleError = ref("");
let scheduleTimer: ReturnType<typeof setTimeout> | undefined;

const mappingFields = [
  { key: "external_id", label: "external_id", required: true },
  { key: "sku", label: "sku", required: true },
  { key: "title", label: "title", required: true },
  { key: "purchase_price", label: "purchase_price", required: true },
  { key: "rrp", label: "rrp", required: false },
  { key: "currency", label: "currency", required: true },
  { key: "availability", label: "availability", required: false },
  { key: "quantity", label: "quantity", required: false },
] as const;
const sourceConfig = computed<Record<string, unknown>>(() => sourceFormat.value === "xlsx"
  ? { sheet_name: sheetName.value, header_row: headerRow.value, data_start_row: headerRow.value + 1 }
  : { item_path: itemPath.value });
const availableSelectors = computed(() => preview.value?.columns ?? []);
const mappingComplete = computed(() => mappingFields.filter((field) => field.required).every((field) => {
  const spec = mapping.value[field.key];
  return Boolean(spec?.selector || spec?.selectors?.length || "constant" in (spec ?? {}));
}));

watch([cronExpression, timezone, step], () => {
  if (step.value !== 3) return;
  if (scheduleTimer) clearTimeout(scheduleTimer);
  scheduleTimer = setTimeout(async () => {
    try {
      nextRuns.value = await priceListsApi.previewSchedule(cronExpression.value, timezone.value);
      scheduleError.value = "";
    } catch (cause) {
      nextRuns.value = [];
      scheduleError.value = getApiErrorMessage(cause, "Проверьте CRON и часовой пояс.");
    }
  }, 300);
}, { immediate: true });

onMounted(async () => {
  if (!editMode.value) return;
  try {
    const item = await priceListsApi.get(priceListId.value);
    blockedStatus.value = item.status === "active" || item.status === "archived" ? item.status : "";
    title.value = item.title;
    sourceUrlDisplay.value = item.source_url_display;
    sourceFormat.value = item.source_format;
    preset.value = item.source_preset === "prom_xml" ? "prom_xml" : "custom";
    itemPath.value = String(item.source_config.item_path ?? "");
    sheetName.value = String(item.source_config.sheet_name ?? "Sheet1");
    headerRow.value = Number(item.source_config.header_row ?? 1);
    mapping.value = { ...item.mapping_config };
    cronExpression.value = item.cron_expression ?? "0 */6 * * *";
    timezone.value = item.timezone;
    newItemPolicy.value = item.new_item_policy;
    missingPolicy.value = item.missing_item_policy;
    missingThreshold.value = item.missing_threshold;
  } catch (cause) {
    error.value = getApiErrorMessage(cause, "Не удалось загрузить настройки прайс-листа.");
  } finally {
    loading.value = false;
  }
});

function promMapping(): MappingConfig {
  return {
    external_id: { selector: "@id", required: true }, sku: { selector: "vendorCode", required: true },
    title: { selector: "name", required: true }, purchase_price: { selector: "price", type: "decimal", required: true },
    rrp: { selector: "priceRRP", type: "decimal" }, currency: { selector: "currencyId", default: "UAH", required: true },
    availability: { selector: "@in_stock" }, quantity: { constant: null },
  };
}
function preparePreset() {
  if (preset.value !== "prom_xml") return;
  sourceFormat.value = "xml";
  itemPath.value = "yml_catalog.shop.offers.offer";
  mapping.value = promMapping();
}
function setSelector(key: string, selector: unknown) {
  mapping.value = { ...mapping.value, [key]: {
    selector: String(selector ?? ""), required: mappingFields.find((field) => field.key === key)?.required,
    ...(key === "purchase_price" || key === "rrp" ? { type: "decimal" as const } : {}),
    ...(key === "quantity" ? { type: "integer" as const } : {}),
    ...(key === "currency" ? { default: "UAH" } : {}),
  } };
}
async function run(action: () => Promise<void>) {
  busy.value = true; error.value = "";
  try { await action(); } catch (cause) { error.value = getApiErrorMessage(cause, "Не удалось сохранить прайс-лист."); } finally { busy.value = false; }
}
function candidate(mappingConfig: MappingConfig) {
  return {
    ...(sourceUrl.value ? { source_url: sourceUrl.value } : {}),
    source_format: sourceFormat.value,
    source_preset: preset.value === "prom_xml" ? "prom_xml" as const : null,
    source_config: sourceConfig.value,
    mapping_config: mappingConfig,
  };
}
async function submitSource() {
  await run(async () => {
    preparePreset();
    if (!editMode.value) {
      const created = await priceListsApi.create({ title: title.value, source_url: sourceUrl.value, source_format: sourceFormat.value, source_preset: preset.value === "prom_xml" ? "prom_xml" : null, source_config: sourceConfig.value });
      priceListId.value = created.id;
      preview.value = await priceListsApi.preview(created.id);
    } else {
      preview.value = await priceListsApi.preview(priceListId.value, candidate({}));
    }
    step.value = 2;
  });
}
async function submitMapping() {
  await run(async () => {
    if (editMode.value) {
      preview.value = await priceListsApi.preview(priceListId.value, candidate(mapping.value));
    } else {
      await priceListsApi.saveMapping(priceListId.value, sourceConfig.value, mapping.value);
      preview.value = await priceListsApi.preview(priceListId.value);
    }
    step.value = 3;
  });
}
async function finish() {
  await run(async () => {
    if (editMode.value) {
      await priceListsApi.updateSettings(priceListId.value, {
        title: title.value,
        ...(sourceUrl.value ? { source_url: sourceUrl.value } : {}),
        source_format: sourceFormat.value,
        source_preset: preset.value === "prom_xml" ? "prom_xml" : null,
        source_config: sourceConfig.value,
        mapping_config: mapping.value,
        cron_expression: cronExpression.value,
        timezone: timezone.value,
        new_item_policy: newItemPolicy.value,
        missing_item_policy: missingPolicy.value,
        missing_threshold: missingThreshold.value,
      });
    } else {
      await priceListsApi.saveSchedule(priceListId.value, { cron_expression: cronExpression.value, timezone: timezone.value, new_item_policy: newItemPolicy.value, missing_item_policy: missingPolicy.value, missing_threshold: missingThreshold.value });
      await priceListsApi.activate(priceListId.value);
    }
    await queryClient.invalidateQueries({ queryKey: priceListKeys.all });
    await router.push(`/purchases/price-lists/${priceListId.value}`);
  });
}
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header><p class="text-sm text-muted-foreground">Закупки / Прайс-листы</p><h1 class="text-2xl font-semibold tracking-tight">{{ editMode ? 'Настройки прайс-листа' : 'Новый прайс-лист' }}</h1></header>
    <div v-if="loading" class="text-sm text-muted-foreground">Загрузка настроек…</div>
    <template v-else>
      <Alert v-if="blockedStatus" variant="destructive"><AlertDescription>{{ blockedStatus === 'active' ? 'Перед редактированием поставьте прайс-лист на паузу.' : 'Сначала восстановите прайс-лист из архива.' }}</AlertDescription></Alert>
      <Alert v-if="error" variant="destructive"><AlertDescription>{{ error }}</AlertDescription></Alert>
      <template v-if="!blockedStatus">
        <ol class="grid grid-cols-3 gap-2" aria-label="Этапы настройки">
          <li v-for="item in [{ n: 1, label: 'Источник' }, { n: 2, label: 'Сопоставление полей' }, { n: 3, label: 'Расписание и правила' }]" :key="item.n" class="flex items-center gap-2 border-b-2 pb-3 text-sm" :class="step >= item.n ? 'border-primary text-foreground' : 'border-muted text-muted-foreground'"><span class="flex size-7 items-center justify-center rounded-full" :class="step >= item.n ? 'bg-primary text-primary-foreground' : 'bg-muted'">{{ step > item.n ? '✓' : item.n }}</span>{{ item.label }}</li>
        </ol>
        <PriceListSourceStep v-if="step === 1" v-model:title="title" v-model:source-url="sourceUrl" v-model:source-format="sourceFormat" v-model:preset="preset" v-model:item-path="itemPath" v-model:sheet-name="sheetName" v-model:header-row="headerRow" :busy="busy" :edit-mode="editMode" :source-url-display="sourceUrlDisplay" @submit="submitSource" />
        <PriceListMappingStep v-else-if="step === 2" :preview="preview" :mapping="mapping" :fields="mappingFields" :available-selectors="availableSelectors" :mapping-complete="mappingComplete" :busy="busy" @back="step = 1" @submit="submitMapping" @set-selector="setSelector" />
        <PriceListScheduleStep v-else v-model:cron-expression="cronExpression" v-model:timezone="timezone" v-model:new-item-policy="newItemPolicy" v-model:missing-policy="missingPolicy" v-model:missing-threshold="missingThreshold" :next-runs="nextRuns" :schedule-error="scheduleError" :busy="busy" :edit-mode="editMode" @back="step = 2" @submit="finish" />
      </template>
      <Button v-else variant="outline" class="self-start" @click="router.push(`/purchases/price-lists/${priceListId}`)">Вернуться к прайс-листу</Button>
    </template>
  </div>
</template>
