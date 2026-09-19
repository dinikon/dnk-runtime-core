<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft, ArrowRight, Check, FileSearch, Loader2 } from "@lucide/vue";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { priceListsApi } from "../api/client";
import type { MappingConfig, PreviewResult, SourceFormat } from "../api/contracts";

const router = useRouter();
const step = ref(1);
const busy = ref(false);
const error = ref("");
const priceListId = ref("");
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
const sourceConfig = computed<Record<string, unknown>>(() =>
  sourceFormat.value === "xlsx"
    ? { sheet_name: sheetName.value, header_row: headerRow.value, data_start_row: headerRow.value + 1 }
    : { item_path: itemPath.value },
);
const availableSelectors = computed(() => preview.value?.columns ?? []);
const mappingComplete = computed(() =>
  mappingFields.filter((field) => field.required).every((field) => {
    const spec = mapping.value[field.key];
    return Boolean(spec?.selector || spec?.selectors?.length || "constant" in (spec ?? {}));
  }),
);

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

function promMapping(): MappingConfig {
  return {
    external_id: { selector: "@id", required: true },
    sku: { selector: "vendorCode", required: true },
    title: { selector: "name", required: true },
    purchase_price: { selector: "price", type: "decimal", required: true },
    rrp: { selector: "priceRRP", type: "decimal" },
    currency: { selector: "currencyId", default: "UAH", required: true },
    availability: { selector: "@in_stock" },
    quantity: { constant: null },
  };
}
function setSelector(key: string, selector: unknown) {
  const value = String(selector ?? "");
  mapping.value = {
    ...mapping.value,
    [key]: {
      selector: value,
      required: mappingFields.find((field) => field.key === key)?.required,
      ...(key === "purchase_price" || key === "rrp" ? { type: "decimal" as const } : {}),
      ...(key === "quantity" ? { type: "integer" as const } : {}),
      ...(key === "currency" ? { default: "UAH" } : {}),
    },
  };
}
async function run(action: () => Promise<void>) {
  busy.value = true;
  error.value = "";
  try { await action(); } catch (cause) { error.value = getApiErrorMessage(cause, "Не удалось сохранить прайс-лист."); } finally { busy.value = false; }
}
async function submitSource() {
  await run(async () => {
    if (preset.value === "prom_xml") {
      sourceFormat.value = "xml";
      itemPath.value = "yml_catalog.shop.offers.offer";
      mapping.value = promMapping();
    }
    const created = await priceListsApi.create({
      title: title.value,
      source_url: sourceUrl.value,
      source_format: sourceFormat.value,
      source_preset: preset.value === "prom_xml" ? "prom_xml" : null,
      source_config: sourceConfig.value,
    });
    priceListId.value = created.id;
    preview.value = await priceListsApi.preview(created.id);
    step.value = 2;
  });
}
async function submitMapping() {
  await run(async () => {
    await priceListsApi.saveMapping(priceListId.value, sourceConfig.value, mapping.value);
    preview.value = await priceListsApi.preview(priceListId.value);
    step.value = 3;
  });
}
async function activate() {
  await run(async () => {
    await priceListsApi.saveSchedule(priceListId.value, {
      cron_expression: cronExpression.value,
      timezone: timezone.value,
      new_item_policy: newItemPolicy.value,
      missing_item_policy: missingPolicy.value,
      missing_threshold: missingThreshold.value,
    });
    await priceListsApi.activate(priceListId.value);
    await router.push(`/purchases/price-lists/${priceListId.value}`);
  });
}
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header><p class="text-sm text-muted-foreground">Закупки / Прайс-листы</p><h1 class="text-2xl font-semibold tracking-tight">Новый прайс-лист</h1></header>
    <ol class="grid grid-cols-3 gap-2" aria-label="Этапы создания">
      <li v-for="item in [{ n: 1, label: 'Источник' }, { n: 2, label: 'Сопоставление полей' }, { n: 3, label: 'Расписание и правила' }]" :key="item.n" class="flex items-center gap-2 border-b-2 pb-3 text-sm" :class="step >= item.n ? 'border-primary text-foreground' : 'border-muted text-muted-foreground'"><span class="flex size-7 items-center justify-center rounded-full" :class="step >= item.n ? 'bg-primary text-primary-foreground' : 'bg-muted'">{{ step > item.n ? '✓' : item.n }}</span>{{ item.label }}</li>
    </ol>
    <Alert v-if="error" variant="destructive"><AlertDescription>{{ error }}</AlertDescription></Alert>

    <form v-if="step === 1" class="grid gap-5" @submit.prevent="submitSource">
      <Card><CardHeader><CardTitle>Источник данных</CardTitle></CardHeader><CardContent class="grid gap-4 md:grid-cols-2">
        <Field class="md:col-span-2"><FieldLabel for="pl-title">Название</FieldLabel><Input id="pl-title" v-model="title" required placeholder="Например, ProteinPlus закупка" /></Field>
        <Field class="md:col-span-2"><FieldLabel for="pl-url">HTTPS URL файла</FieldLabel><Input id="pl-url" v-model="sourceUrl" type="url" required placeholder="https://partner.example/price.xlsx" /></Field>
        <Field><FieldLabel>Тип источника</FieldLabel><Select v-model="preset"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="custom">Произвольный файл</SelectItem><SelectItem value="prom_xml">Prom XML</SelectItem></SelectContent></Select></Field>
        <Field><FieldLabel>Формат</FieldLabel><Select v-model="sourceFormat" :disabled="preset === 'prom_xml'"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="xml">XML</SelectItem><SelectItem value="yaml">YAML</SelectItem><SelectItem value="xlsx">XLSX</SelectItem></SelectContent></Select></Field>
        <template v-if="sourceFormat === 'xlsx'"><Field><FieldLabel for="sheet-name">Лист</FieldLabel><Input id="sheet-name" v-model="sheetName" /></Field><Field><FieldLabel for="header-row">Строка заголовков</FieldLabel><Input id="header-row" v-model.number="headerRow" type="number" min="1" /></Field></template>
        <Field v-else class="md:col-span-2"><FieldLabel for="item-path">Путь к элементам</FieldLabel><Input id="item-path" v-model="itemPath" :required="preset === 'custom'" placeholder="root.shop.offers.offer" /></Field>
      </CardContent></Card>
      <div class="flex justify-end"><Button type="submit" :disabled="busy"><Loader2 v-if="busy" class="animate-spin" /><FileSearch v-else />Предзагрузить<ArrowRight /></Button></div>
    </form>

    <form v-else-if="step === 2" class="grid min-h-0 gap-4" @submit.prevent="submitMapping">
      <div class="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
        <Card><CardHeader><CardTitle>Предпросмотр источника</CardTitle></CardHeader><CardContent class="overflow-auto">
          <Table v-if="preview?.rows.length"><TableHeader><TableRow><TableHead v-for="key in Object.keys(preview.rows[0]?.values ?? {})" :key="key">{{ key }}</TableHead></TableRow></TableHeader><TableBody><TableRow v-for="row in preview.rows.slice(0, 8)" :key="row.row_number"><TableCell v-for="key in Object.keys(preview.rows[0]?.values ?? {})" :key="key">{{ row.values[key] ?? '—' }}</TableCell></TableRow></TableBody></Table>
          <div v-else class="min-h-48"><p class="text-sm text-muted-foreground">Найдены поля источника:</p><div class="mt-3 flex flex-wrap gap-2"><span v-for="column in availableSelectors" :key="column" class="rounded-md border bg-muted/40 px-2 py-1 text-sm">{{ column }}</span><span v-if="!availableSelectors.length" class="text-sm text-muted-foreground">Для XML/YAML введите селекторы вручную.</span></div></div>
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Сопоставление полей</CardTitle></CardHeader><CardContent class="grid gap-3">
          <Field v-for="field in mappingFields" :key="field.key"><FieldLabel :for="`mapping-${field.key}`">{{ field.label }}<span v-if="field.required" class="text-destructive"> *</span></FieldLabel>
            <Select v-if="availableSelectors.length" :model-value="mapping[field.key]?.selector" @update:model-value="(value) => setSelector(field.key, value)"><SelectTrigger :id="`mapping-${field.key}`"><SelectValue placeholder="Выберите колонку" /></SelectTrigger><SelectContent><SelectItem v-for="column in availableSelectors" :key="column" :value="column">{{ column }}</SelectItem></SelectContent></Select>
            <Input v-else :id="`mapping-${field.key}`" :model-value="mapping[field.key]?.selector ?? ''" placeholder="Селектор или @атрибут" @update:model-value="(value) => setSelector(field.key, value)" />
          </Field>
          <div class="mt-2 flex items-center gap-2 rounded-md bg-muted p-3 text-sm"><Check class="size-4" />{{ mappingComplete ? 'Все обязательные поля сопоставлены' : 'Заполните обязательные поля' }}</div>
        </CardContent></Card>
      </div>
      <div class="flex justify-between"><Button type="button" variant="outline" @click="step = 1"><ArrowLeft />Назад</Button><Button type="submit" :disabled="busy || !mappingComplete">Проверить и продолжить<ArrowRight /></Button></div>
    </form>

    <form v-else class="grid gap-5" @submit.prevent="activate">
      <Card><CardHeader><CardTitle>Расписание и обработка позиций</CardTitle></CardHeader><CardContent class="grid gap-4 md:grid-cols-2">
        <Field><FieldLabel for="cron">CRON</FieldLabel><Input id="cron" v-model="cronExpression" required /><p class="text-xs text-muted-foreground">Например, 0 */6 * * * — каждые 6 часов.</p></Field>
        <Field><FieldLabel for="timezone">Часовой пояс</FieldLabel><Input id="timezone" v-model="timezone" required /></Field>
        <Field><FieldLabel>Если появилась новая позиция</FieldLabel><Select v-model="newItemPolicy"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="create">Создать оффер</SelectItem><SelectItem value="quarantine">На проверку</SelectItem><SelectItem value="ignore">Игнорировать</SelectItem></SelectContent></Select></Field>
        <Field><FieldLabel>Если позиция исчезла</FieldLabel><Select v-model="missingPolicy"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="mark_out_of_stock">Установить «Нет в наличии»</SelectItem><SelectItem value="mark_missing">Отметить отсутствующей</SelectItem><SelectItem value="archive">Архивировать</SelectItem><SelectItem value="keep_last">Оставить без изменений</SelectItem></SelectContent></Select></Field>
        <Field><FieldLabel for="threshold">После скольких загрузок</FieldLabel><Input id="threshold" v-model.number="missingThreshold" type="number" min="1" max="100" /></Field>
        <div class="rounded-lg border bg-muted/30 p-3 md:col-span-2"><p class="text-sm font-medium">Следующие запуски</p><p v-if="scheduleError" class="mt-2 text-sm text-destructive">{{ scheduleError }}</p><ol v-else class="mt-2 grid gap-1 text-sm text-muted-foreground"><li v-for="run in nextRuns" :key="run">{{ new Date(run).toLocaleString('uk-UA', { timeZone: timezone }) }}</li></ol></div>
      </CardContent></Card>
      <div class="flex justify-between"><Button type="button" variant="outline" @click="step = 2"><ArrowLeft />Назад</Button><Button type="submit" :disabled="busy || Boolean(scheduleError) || nextRuns.length !== 5"><Loader2 v-if="busy" class="animate-spin" />Создать и запустить</Button></div>
    </form>
  </div>
</template>
