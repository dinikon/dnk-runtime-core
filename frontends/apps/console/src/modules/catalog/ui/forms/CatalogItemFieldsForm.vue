<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import CatalogMeasurementField from "./CatalogMeasurementField.vue";
import ProductRichText from "../product/ProductRichText.vue";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { clone } from "../../model/clone";
import type { CatalogItem, CatalogAttribute } from "../../model/catalog.types";
import type {
  ProductSection,
  ProductPrice,
  ProductWeight,
  ProductStock,
  ProductDimensions,
  ProductMetadata,
  ProductAttribute,
} from "../../model/product.types";
const props = defineProps<{
  item: CatalogItem;
  section: ProductSection;
  locale: string;
  pending: boolean;
  reset: number;
  attributes: CatalogAttribute[];
  schemaVersion: number;
  validationError?: string;
}>();
const emit = defineEmits<{
  save: [value: Record<string, unknown>];
  dirty: [value: boolean];
}>();
const stockStatusLabels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_backorder: "Предзаказ",
};
const contentLabels: Record<string, string> = {
  name: "Название",
  desc: "Описание",
  short_desc: "Краткое описание",
};
const dirty = ref(false),
  text = ref<Record<string, string>>({}),
  status = ref("draft"),
  sku = ref(""),
  virtual = ref(false),
  price = ref<ProductPrice | null>(null),
  stock = ref<ProductStock>({
    manage_stock: false,
    stock_quantity: null,
    stock_status: "in_stock",
    backorders: "no",
  }),
  weight = ref<ProductWeight | null>(null),
  dimensions = ref<ProductDimensions>({
    length: null,
    width: null,
    height: null,
  }),
  metadata = ref<ProductMetadata[]>([]),
  assignments = ref<ProductAttribute[]>([]);
function mark() {
  dirty.value = true;
  emit("dirty", true);
  void nextTick(submit);
}
function resetFields() {
  const own = props.item;
  text.value = clone(own.content ?? {});
  status.value = own.status;
  sku.value = own.sku ?? "";
  virtual.value = clone(own.virtual);
  price.value = clone(own.price_specification);
  stock.value = clone(own.stock);
  weight.value = clone(own.weight);
  dimensions.value = clone(
    own.dimensions ?? { length: null, width: null, height: null },
  );
  metadata.value = clone(own.metadata);
  assignments.value = clone(own.attributes);
  dirty.value = false;
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.item,
  () => {
    if (!dirty.value) resetFields();
  },
);
function contentEnabled(code: string, enabled: boolean) {
  if (enabled) text.value[code] = props.item.content?.[code] ?? "";
  else delete text.value[code];
  mark();
}
function priceMode(event: Event) {
  price.value =
    (event.target as HTMLSelectElement).value === "set"
      ? {
          regular_price: "0",
          currency: "UAH",
          sale_price: null,
          date_on_sale_from: null,
          date_on_sale_to: null,
        }
      : null;
  mark();
}
function stockMode(event: Event) {
  const managed = (event.target as HTMLInputElement).checked;
  stock.value = managed
    ? {
        manage_stock: true,
        stock_quantity: 0,
        stock_status: null,
        backorders: "no",
      }
    : {
        manage_stock: false,
        stock_quantity: null,
        stock_status: "in_stock",
        backorders: "no",
      };
  mark();
}
const selectedAttribute = ref("");
const availableAttributes = computed(() =>
  props.attributes.filter(
    (a) => !assignments.value.some((v) => v.attribute_id === a.id),
  ),
);
function addAttribute() {
  const a = availableAttributes.value.find(
    (a) => a.id === selectedAttribute.value,
  );
  if (a) {
    assignments.value.push({
      attribute_id: a.id,
      option_ids: [],
      visible: true,
      position: assignments.value.length,
    });
    mark();
  }
}
function localDate(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
function saleDate(
  field: "date_on_sale_from" | "date_on_sale_to",
  event: Event,
): void {
  if (!price.value) return;
  const value = (event.target as HTMLInputElement).value;
  price.value[field] = value ? new Date(value).toISOString() : null;
}
function submit() {
  const section = props.section;
  let value: Record<string, unknown> = {};
  if (section === "content")
    value = {
      expected_schema_version: props.schemaVersion,
      values: text.value,
    };
  if (section === "status") value = { status: status.value };
  if (section === "sku") value = { sku: sku.value || null };
  if (section === "virtual") value = { virtual: virtual.value };
  if (section === "price") value = { price: price.value };
  if (section === "stock") value = { stock: stock.value };
  if (section === "measurements")
    value = { weight: weight.value, dimensions: dimensions.value };
  if (section === "metadata")
    value = {
      metadata: metadata.value.map((v, position) => ({
        ...v,
        position,
      })),
    };
  if (section === "attributes")
    value = {
      attributes: assignments.value.map((v, position) => ({
        ...v,
        position,
      })),
    };
  emit("save", value);
}
</script>
<template>
  <form class="flex flex-col gap-4" @submit.prevent="submit">
    <fieldset
      :aria-invalid="!!validationError || undefined"
      :disabled="pending"
      class="flex flex-col gap-4"
      @input="section !== 'content' && mark()"
      @change="section !== 'content' && mark()"
    >
      <template v-if="section === 'content'">
        <FieldGroup>
          <Field v-for="code in ['name', 'desc', 'short_desc']" :key="code">
            <FieldLabel :for="`${item.id}-content-${code}`">{{
              contentLabels[code]
            }}</FieldLabel>
            <label
              v-if="code !== 'name'"
              class="flex items-center gap-2 text-sm"
              ><input
                type="checkbox"
                :checked="text[code] !== undefined"
                @change="
                  contentEnabled(
                    code,
                    ($event.target as HTMLInputElement).checked,
                  )
                "
              />Добавить описание</label
            >
            <Input
              v-if="code === 'name'"
              :id="`${item.id}-content-${code}`"
              :model-value="text[code] ?? ''"
              placeholder="Название товара"
              required
              @update:model-value="
                text[code] = String($event);
                mark();
              "
            />
            <ProductRichText
              v-else-if="text[code] !== undefined"
              :model-value="text[code] ?? ''"
              :label="contentLabels[code]!"
              :disabled="pending"
              @update:model-value="
                text[code] = $event;
                mark();
              "
            />
          </Field>
        </FieldGroup>
      </template>
      <label v-else-if="section === 'status'" class="block"
        >Статус<select
          v-model="status"
          class="w-full rounded border bg-background p-2"
        >
          <option value="draft">Черновик</option>
          <option value="active">Активный</option>
          <option value="archived">Архив</option>
        </select></label
      >
      <label v-else-if="section === 'sku'" class="block"
        >SKU<input
          v-model="sku"
          maxlength="128"
          class="w-full rounded border bg-background p-2"
      /></label>
      <template v-else-if="section === 'virtual'">
        <label class="flex flex-wrap gap-2"
          ><input v-model="virtual" type="checkbox" /> Виртуальный товар</label
        >
      </template>
      <template v-else-if="section === 'price'"
        ><select
          :value="price ? 'set' : 'clear'"
          aria-label="Цена"
          class="w-full rounded border bg-background p-2"
          @change="priceMode"
        >
          <option value="set">Задать цену</option>
          <option value="clear">Цена не задана</option>
        </select>
        <div v-if="price" class="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
          <label
            >Обычная цена<input
              v-model="price.regular_price"
              inputmode="decimal"
              class="w-full rounded border bg-background p-2"
              required /></label
          ><label
            >Валюта<input
              v-model="price.currency"
              class="w-full rounded border bg-background p-2"
              maxlength="3"
              required /></label
          ><label
            >Акционная цена<input
              :value="price.sale_price ?? ''"
              inputmode="decimal"
              class="w-full rounded border bg-background p-2"
              @input="
                price.sale_price =
                  ($event.target as HTMLInputElement).value || null
              " /></label
          ><label
            v-for="field in ['date_on_sale_from', 'date_on_sale_to'] as const"
            :key="field"
            >{{ field === "date_on_sale_from" ? "Начало акции" : "Конец акции"
            }}<input
              :value="localDate(price[field])"
              type="datetime-local"
              class="w-full rounded border bg-background p-2"
              @input="saleDate(field, $event)"
          /></label>
        </div>
        <p class="text-sm text-muted-foreground">
          Текущая цена: {{ item.price ?? "Не задана" }}
          {{ item.price_specification?.currency }}
        </p></template
      >
      <template v-else-if="section === 'stock'">
        <label class="flex flex-wrap gap-2"
          ><input
            :checked="stock.manage_stock"
            type="checkbox"
            @change="stockMode"
          />
          Учитывать собственное количество</label
        >
        <label v-if="stock.manage_stock" class="block"
          >Количество
          <input
            v-model.number="stock.stock_quantity"
            type="number"
            step="1"
            required
            class="w-full rounded border bg-background p-2"
          />
        </label>
        <select
          v-if="!stock.manage_stock"
          v-model="stock.stock_status"
          aria-label="Наличие"
          class="w-full rounded border bg-background p-2"
        >
          <option value="in_stock">В наличии</option>
          <option value="out_of_stock">Нет в наличии</option>
          <option value="on_backorder">Предзаказ</option>
        </select>
        <label v-if="stock.manage_stock" class="block"
          >Предзаказ
          <select
            v-model="stock.backorders"
            class="w-full rounded border bg-background p-2"
          >
            <option value="no">Запрещён</option>
            <option value="notify">С уведомлением</option>
            <option value="yes">Разрешён</option>
          </select>
        </label>
        <p class="text-sm text-muted-foreground">
          Текущее наличие:
          {{ stockStatusLabels[item.stock_status] ?? "Неизвестно" }}
        </p>
        <p class="text-sm text-muted-foreground">
          {{
            item.available_for_sale
              ? "Доступен для продажи"
              : "Недоступен для продажи"
          }}
        </p>
      </template>
      <template v-else-if="section === 'measurements'">
        <div class="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
          <CatalogMeasurementField
            v-model="weight"
            label="Вес"
            :units="['g', 'kg'] as const"
            default-unit="g"
            :effective="item.weight"
          />
          <CatalogMeasurementField
            v-for="field in ['length', 'width', 'height'] as const"
            :key="field"
            v-model="dimensions[field]"
            :label="
              field === 'length'
                ? 'Длина'
                : field === 'width'
                  ? 'Ширина'
                  : 'Высота'
            "
            :units="['cm', 'm'] as const"
            default-unit="cm"
            :effective="item.dimensions?.[field] ?? null"
          />
        </div>
      </template>
      <template v-else-if="section === 'metadata'"
        ><div
          v-for="(entry, index) in metadata"
          :key="index"
          class="grid min-w-0 grid-cols-1 gap-2 rounded border p-3 sm:grid-cols-2"
        >
          <input
            v-model="entry.key"
            aria-label="Ключ"
            placeholder="Ключ"
            class="rounded border bg-background p-2"
          /><select
            v-model="entry.value_type"
            aria-label="Тип значения"
            class="rounded border bg-background p-2"
            @change="entry.value = entry.value_type === 'boolean' ? false : ''"
          >
            <option value="text">Текст</option>
            <option value="decimal">Число</option>
            <option value="boolean">Да/Нет</option></select
          ><label v-if="entry.value_type === 'boolean'"
            ><input v-model="entry.value" type="checkbox" /> Да</label
          ><input
            v-else
            v-model="entry.value"
            aria-label="Значение"
            class="rounded border bg-background p-2"
          /><Button
            type="button"
            variant="ghost"
            @click="
              metadata.splice(index, 1);
              mark();
            "
            >Убрать ключ</Button
          >
        </div>
        <Button
          type="button"
          variant="outline"
          @click="
            metadata.push({
              key: '',
              value_type: 'text',
              value: '',
              position: metadata.length,
            });
            mark();
          "
          >Добавить поле</Button
        >
        <p class="text-sm text-muted-foreground">
          Текущие значения:
          {{
            item.metadata.map((v) => `${v.key}: ${v.value}`).join(", ") || "Нет"
          }}
        </p></template
      >
      <template v-else-if="section === 'attributes'"
        ><div
          v-for="(assignment, index) in assignments"
          :key="assignment.attribute_id"
          class="flex flex-col gap-2 rounded border p-3"
        >
          <span>{{
            attributes.find((a) => a.id === assignment.attribute_id)?.label ??
            attributes.find((a) => a.id === assignment.attribute_id)?.code
          }}</span
          ><label class="ml-2"
            ><input v-model="assignment.visible" type="checkbox" />
            Видимый</label
          >
          <div class="flex flex-wrap gap-2">
            <label
              v-for="o in attributes.find(
                (a) => a.id === assignment.attribute_id,
              )?.options ?? []"
              :key="o.id"
              ><input
                v-model="assignment.option_ids"
                type="checkbox"
                :value="o.id"
              />
              {{ o.label ?? o.code }}</label
            >
          </div>
          <Button
            type="button"
            variant="ghost"
            @click="
              assignments.splice(index, 1);
              mark();
            "
            >Убрать назначение</Button
          >
        </div>
        <label class="flex flex-col gap-2 text-sm"
          >Добавить общую характеристику<select
            v-model="selectedAttribute"
            class="w-full rounded-md border bg-background p-2"
          >
            <option value="">Выберите характеристику</option>
            <option
              v-for="attribute in availableAttributes"
              :key="attribute.id"
              :value="attribute.id"
            >
              {{ attribute.label ?? attribute.code }}
            </option>
          </select></label
        >
        <Button
          type="button"
          variant="outline"
          :disabled="
            !selectedAttribute ||
            !availableAttributes.some((a) => a.id === selectedAttribute)
          "
          @click="addAttribute"
          >Добавить характеристику</Button
        ></template
      >
    </fieldset>
    <p v-if="validationError" role="alert" class="text-sm text-destructive">
      {{ validationError }}
    </p>
  </form>
</template>
