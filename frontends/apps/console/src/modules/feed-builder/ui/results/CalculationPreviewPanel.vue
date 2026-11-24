<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { Field, FieldLabel, FieldDescription } from "@/components/ui/field";
import type {
  CalculationPreview,
  CatalogPriceChoice,
  TraceValue,
} from "../../model/feed-calculation.types";
import type { FieldKind } from "../../model/feed-schema.types";
const props = defineProps<{
  fieldKind?: FieldKind;
  locale: string;
  locales: { code: string; name: string }[];
  products: CatalogPriceChoice[];
  productsTotal: number;
  variants: CatalogPriceChoice[];
  variantsTotal: number;
  search: string;
  offset: number;
  variantOffset: number;
  root: CatalogPriceChoice | null;
  variant: CatalogPriceChoice | null;
  loading: boolean;
  variantsLoading: boolean;
  sourceError: string;
  error: string;
  pending: boolean;
  stale: boolean;
  result: CalculationPreview | null;
  canPreview: boolean;
  disabled: boolean;
}>();
const emit = defineEmits<{
  locale: [value: string];
  search: [value: string];
  offset: [value: number];
  variantOffset: [value: number];
  root: [value: CatalogPriceChoice];
  variant: [value: CatalogPriceChoice];
  preview: [];
  retry: [];
}>();
function chooseRoot(value: string): void {
  const item = props.products.find((p) => p.id === value);
  if (item) emit("root", item);
}
function chooseVariant(value: string): void {
  const item = props.variants.find((p) => p.id === value);
  if (item) emit("variant", item);
}
const branch = computed(() => {
  const value = props.result;
  if (!value) return "";
  if (value.steps.some((step) => step.operation === "THEN")) return "THEN";
  if (!value.selectedRuleId)
    return value.usedDefault
      ? "ELSE"
      : value.validationStatus === "INVALID"
        ? "Ошибка условия"
        : "Источник";
  const index = value.steps.find(
    (s) => s.ruleId === value.selectedRuleId && s.path[0] === "rules",
  )?.path[1];
  return typeof index === "number" ? `IF · ${index + 1}` : "IF";
});
function display(value: TraceValue): string {
  return value === null
    ? "Отсутствует"
    : Array.isArray(value)
      ? value.join(", ")
      : String(value);
}
</script>
<template>
  <section
    class="flex min-w-0 flex-col gap-4 rounded-lg border p-4"
    :aria-label="fieldKind === 'money' ? 'Предпросмотр цены' : 'Предпросмотр значения'"
  >
    <div>
      <h2 class="text-lg font-semibold">Предпросмотр на товаре</h2>
      <p class="text-sm text-muted-foreground">
        Проверяет текущий ввод без сохранения схемы на данных Catalog.
      </p>
    </div>
    <Field
      ><FieldLabel for="price-preview-locale">Язык названий каталога</FieldLabel
      ><Select
        :model-value="locale"
        :disabled="disabled"
        @update:model-value="emit('locale', String($event))"
        ><SelectTrigger id="price-preview-locale"><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem v-for="l in locales" :key="l.code" :value="l.code"
              >{{ l.name }} ({{ l.code }})</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    >
    <Field
      ><FieldLabel for="price-preview-search">Найти товар</FieldLabel
      ><Input
        id="price-preview-search"
        :model-value="search"
        :disabled="disabled"
        placeholder="Название или SKU"
        @update:model-value="emit('search', String($event))"
    /></Field>
    <p v-if="loading" role="status" class="text-sm text-muted-foreground">
      Загрузка товаров…
    </p>
    <Alert v-if="sourceError" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        >{{ sourceError
        }}<Button type="button" variant="outline" @click="emit('retry')"
          >Повторить загрузку</Button
        ></AlertDescription
      ></Alert
    >
    <p
      v-if="!loading && !sourceError && !products.length"
      class="text-sm text-muted-foreground"
    >
      Товары не найдены.
    </p>
    <Field
      ><FieldLabel for="price-preview-product">Товар каталога</FieldLabel
      ><Select
        :model-value="root?.id"
        :disabled="disabled || loading || !products.length"
        @update:model-value="chooseRoot(String($event))"
        ><SelectTrigger id="price-preview-product"
          ><SelectValue
            :placeholder="root?.title ?? 'Выберите товар'" /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem v-for="p in products" :key="p.id" :value="p.id"
              >{{ p.title }}{{ p.sku ? ` · ${p.sku}` : ""
              }}{{ p.kind === "variable" ? " · Вариативный" : "" }}</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    >
    <div
      v-if="offset > 0 || productsTotal > 20"
      class="flex items-center gap-2"
    >
      <Button
        type="button"
        variant="outline"
        :disabled="disabled || loading || offset === 0"
        @click="emit('offset', Math.max(0, offset - 20))"
        >Предыдущие товары</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="disabled || loading || offset + 20 >= productsTotal"
        @click="emit('offset', offset + 20)"
        >Следующие товары</Button
      >
    </div>
    <template v-if="root?.kind === 'variable'">
      <Field
        ><FieldLabel for="price-preview-variant">Конкретный вариант</FieldLabel
        ><Select
          :model-value="variant?.id"
          :disabled="disabled || variantsLoading || !variants.length"
          @update:model-value="chooseVariant(String($event))"
          ><SelectTrigger id="price-preview-variant"
            ><SelectValue
              :placeholder="
                variant?.title ?? 'Выберите вариант'
              " /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem v-for="p in variants" :key="p.id" :value="p.id"
                >{{ p.title }}{{ p.sku ? ` · ${p.sku}` : "" }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        ><FieldDescription
          >Выберите конкретный вариант: его собственная цена используется в
          расчёте.</FieldDescription
        ></Field
      >
      <p v-if="variantsLoading" role="status">Загрузка вариантов…</p>
      <p
        v-else-if="!variants.length && !sourceError"
        class="text-sm text-muted-foreground"
      >
        У товара пока нет вариантов.
      </p>
      <div
        v-if="variantOffset > 0 || variantsTotal > 20"
        class="flex flex-wrap gap-2"
      >
        <Button
          type="button"
          variant="outline"
          :disabled="disabled || variantsLoading || variantOffset === 0"
          @click="emit('variantOffset', Math.max(0, variantOffset - 20))"
          >Предыдущие варианты</Button
        ><Button
          type="button"
          variant="outline"
          :disabled="
            disabled || variantsLoading || variantOffset + 20 >= variantsTotal
          "
          @click="emit('variantOffset', variantOffset + 20)"
          >Следующие варианты</Button
        >
      </div>
    </template>
    <Button type="button" :disabled="!canPreview" @click="emit('preview')">{{
      pending ? "Рассчитываем…" : fieldKind === "money" ? "Рассчитать цену" : "Рассчитать значение"
    }}</Button>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <Alert v-if="stale"
      ><AlertDescription
        >Результат устарел. Настройки, товар или период акции изменились.
        Повторите расчёт.</AlertDescription
      ></Alert
    >
    <div
      v-if="result"
      class="flex min-w-0 flex-col gap-3"
      :class="stale ? 'opacity-60' : ''"
      aria-live="polite"
    >
      <div v-if="result.resolvedValue !== null" class="rounded-md bg-muted p-4">
        <p class="text-sm text-muted-foreground">
          {{
            fieldKind === "money"
              ? stale ? "Предыдущая цена" : "Рассчитанная цена"
              : stale ? "Предыдущее значение" : "Результат"
          }}
        </p>
        <p
          class="break-all text-2xl font-semibold"
          data-testid="calculated-price"
        >
          <template v-if="typeof result.resolvedValue === 'object'">
            {{ result.resolvedValue.amount }}<span v-if="result.resolvedValue.currency" class="ml-1">{{ result.resolvedValue.currency }}</span>
          </template>
          <template v-else>{{ String(result.resolvedValue) }}</template>
        </p>
      </div>
      <p v-else-if="result.validationStatus === 'VALID'" class="text-sm">Значение отсутствует</p>
      <p class="text-sm">Ветка: {{ branch }}</p>
      <Alert
        v-for="(issue, index) in result.issues"
        :key="index"
        variant="destructive"
        ><AlertDescription
          ><p>{{ issue.message }}</p>
          <p class="break-all text-xs">
            {{ issue.code }} · {{ issue.path.join(" → ")
            }}{{ issue.ruleId ? ` · IF ${issue.ruleId}` : "" }}
          </p></AlertDescription
        ></Alert
      >
      <details>
        <summary class="cursor-pointer text-sm font-medium">
          Исходные значения и шаги
        </summary>
        <div class="mt-3 flex flex-col gap-3 text-sm">
          <dl class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-2">
            <template v-for="p in result.parameters" :key="p.id"
              ><dt class="break-all text-muted-foreground">{{ p.id }}</dt>
              <dd class="break-all">{{ display(p.value) }}</dd></template
            >
          </dl>
          <ol class="flex flex-col gap-2">
            <li
              v-for="(step, index) in result.steps"
              :key="index"
              class="break-all rounded border p-2"
            >
              {{ step.operation }} → {{ display(step.value)
              }}<span class="block text-xs text-muted-foreground">{{
                step.path.join(" → ")
              }}</span>
            </li>
          </ol>
        </div>
      </details>
      <p class="break-all text-xs text-muted-foreground">
        Снимок {{ result.asOf }} · версия Feed {{ result.version }} ·
        вычислитель {{ result.engineVersion
        }}{{ result.validUntil ? ` · до ${result.validUntil}` : "" }}
      </p>
    </div>
  </section>
</template>
