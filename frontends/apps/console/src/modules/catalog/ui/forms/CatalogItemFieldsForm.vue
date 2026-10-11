<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { clone } from "../../model/clone";
import type { CatalogItem, CatalogAttribute } from "../../model/catalog.types";
import type {
  ItemSection,
  OverrideDTO,
  PriceDTO,
  StockDTO,
  DimensionsDTO,
  MetadataDTO,
  AttributeDTO,
} from "../../api/catalog.dto";
const props = defineProps<{
  item: CatalogItem;
  section: ItemSection;
  locale: string;
  pending: boolean;
  reset: number;
  attributes: CatalogAttribute[];
}>();
const emit = defineEmits<{
  save: [value: Record<string, unknown>];
  dirty: [value: boolean];
  inherit: [];
}>();
const contentLabels: Record<string, string> = {
  name: "Название",
  desc: "Описание",
  short_desc: "Краткое описание",
};
const dirty = ref(false),
  text = ref<Record<string, OverrideDTO<string>>>({}),
  status = ref("draft"),
  sku = ref(""),
  virtual = ref<OverrideDTO<boolean>>({ mode: "set", value: false }),
  price = ref<OverrideDTO<PriceDTO>>({ mode: "clear", value: null }),
  stock = ref<StockDTO | null>(null),
  weight = ref<OverrideDTO<string>>({ mode: "clear", value: null }),
  dimensions = ref<OverrideDTO<DimensionsDTO>>({ mode: "clear", value: null }),
  metadata = ref<MetadataDTO[]>([]),
  assignments = ref<AttributeDTO[]>([]);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function resetFields() {
  const own = props.item.own;
  text.value = clone(own.translations[props.locale] ?? {});
  status.value = own.status;
  sku.value = own.sku ?? "";
  virtual.value = clone(own.virtual);
  price.value = clone(own.price);
  stock.value = clone(own.stock);
  weight.value = clone(own.weight);
  dimensions.value = clone(own.dimensions);
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
function contentMode(code: string, mode: string) {
  if (mode === "inherit") delete text.value[code];
  else
    text.value[code] = {
      mode: mode as "set" | "clear",
      value:
        mode === "set" ? (props.item.effective.content?.[code] ?? "") : null,
    };
  mark();
}
function priceMode() {
  price.value.value =
    price.value.mode === "set"
      ? clone(
          props.item.effective.price_specification ?? {
            regular_price: "0",
            currency: "UAH",
            sale_price: null,
            date_on_sale_from: null,
            date_on_sale_to: null,
          },
        )
      : null;
  mark();
}
function dimensionsMode() {
  dimensions.value.value =
    dimensions.value.mode === "set"
      ? clone(
          props.item.effective.dimensions ?? {
            length: "0",
            width: "0",
            height: "0",
          },
        )
      : null;
  mark();
}
function stockMode(event: Event) {
  const mode = (event.target as HTMLSelectElement).value;
  stock.value =
    mode === "unknown"
      ? null
      : mode === "parent"
        ? {
            manage_stock: "parent",
            stock_quantity: null,
            stock_status: null,
            backorders: null,
          }
        : mode === "own"
          ? {
              manage_stock: "own",
              stock_quantity: 0,
              stock_status: null,
              backorders: "no",
            }
          : {
              manage_stock: "none",
              stock_quantity: null,
              stock_status: "in_stock",
              backorders: "no",
            };
  mark();
}
function addAttribute() {
  const a = props.attributes.find(
    (a) =>
      !assignments.value.some((v) => v.attribute_id === a.id) &&
      !props.item.own.axes.some((v) => v.attribute_id === a.id) &&
      !props.item.own.selection.values.some(([id]) => id === a.id),
  );
  if (a) {
    assignments.value.push({
      attribute_id: a.id,
      option_ids: [],
      visible: true,
      position: assignments.value.length,
      mode: "set",
    });
    mark();
  }
}
function submit() {
  const section = props.section;
  let value: Record<string, unknown> = {};
  if (section === "content")
    value = { expected_schema_version: 1, values: text.value };
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
        value_type: v.mode === "clear" ? null : v.value_type,
        value: v.mode === "clear" ? null : v.value,
      })),
    };
  if (section === "attributes")
    value = {
      attributes: assignments.value.map((v, position) => ({
        ...v,
        position,
        option_ids: v.mode === "clear" ? [] : v.option_ids,
      })),
    };
  emit("save", value);
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="submit">
    <fieldset
      :disabled="pending"
      class="space-y-4"
      @input="mark"
      @change="mark"
    >
      <template v-if="section === 'content'"
        ><div
          v-for="code in ['name', 'desc', 'short_desc']"
          :key="code"
          class="space-y-2"
        >
          <label :for="`content-${code}`">{{ contentLabels[code] }}</label
          ><select
            :aria-label="`Источник ${code}`"
            class="w-full rounded border bg-background p-2"
            :value="
              text[code]?.mode ?? (item.kind === 'variant' ? 'inherit' : 'set')
            "
            @change="
              contentMode(code, ($event.target as HTMLSelectElement).value)
            "
          >
            <option v-if="item.kind === 'variant'" value="inherit">
              Наследовать
            </option>
            <option value="set">Собственное значение</option>
            <option v-if="code !== 'name'" value="clear">
              Очистить
            </option></select
          ><textarea
            v-if="text[code]?.mode === 'set'"
            :id="`content-${code}`"
            v-model="text[code]!.value"
            class="w-full rounded border bg-background p-2"
            :rows="code === 'name' ? 1 : 4"
          />
          <p class="text-sm text-muted-foreground">
            Эффективно: {{ item.effective.content?.[code] ?? "Не задано" }} ·
            {{ item.effective.origins[code]?.source }}
          </p>
          <Button
            v-if="!text[code] && item.kind !== 'variant'"
            type="button"
            variant="outline"
            @click="contentMode(code, 'set')"
            >Добавить значение</Button
          >
        </div>
        <Button
          v-if="item.kind === 'variant'"
          type="button"
          variant="outline"
          @click="emit('inherit')"
          >Унаследовать весь перевод</Button
        ></template
      >
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
      <template v-else-if="section === 'virtual'"
        ><select
          v-model="virtual.mode"
          aria-label="Источник virtual"
          class="w-full rounded border bg-background p-2"
          @change="
            virtual.value =
              virtual.mode === 'set' ? item.effective.virtual : null
          "
        >
          <option v-if="item.kind === 'variant'" value="inherit">
            Наследовать
          </option>
          <option value="set">Собственное значение</option></select
        ><label v-if="virtual.mode === 'set'" class="flex gap-2"
          ><input v-model="virtual.value" type="checkbox" /> Виртуальный
          товар</label
        ></template
      >
      <template v-else-if="section === 'price'"
        ><select
          v-model="price.mode"
          aria-label="Источник цены"
          class="w-full rounded border bg-background p-2"
          @change="priceMode"
        >
          <option v-if="item.kind === 'variant'" value="inherit">
            Наследовать
          </option>
          <option value="set">Задать цену</option>
          <option value="clear">Цена не задана</option>
        </select>
        <div v-if="price.value" class="grid gap-3 sm:grid-cols-2">
          <label
            >Обычная цена<input
              v-model="price.value.regular_price"
              inputmode="decimal"
              class="w-full rounded border bg-background p-2"
              required /></label
          ><label
            >Валюта<input
              v-model="price.value.currency"
              class="w-full rounded border bg-background p-2"
              maxlength="3"
              required /></label
          ><label
            >Акционная цена<input
              :value="price.value.sale_price ?? ''"
              inputmode="decimal"
              class="w-full rounded border bg-background p-2"
              @input="
                price.value.sale_price =
                  ($event.target as HTMLInputElement).value || null
              " /></label
          ><label
            v-for="field in ['date_on_sale_from', 'date_on_sale_to'] as const"
            :key="field"
            >{{
              field === "date_on_sale_from"
                ? "Начало акции (ISO UTC)"
                : "Конец акции (ISO UTC)"
            }}<input
              :value="price.value[field] ?? ''"
              placeholder="2026-10-11T00:00:00Z"
              class="w-full rounded border bg-background p-2"
              @input="
                price.value[field] =
                  ($event.target as HTMLInputElement).value || null
              "
          /></label>
        </div>
        <p class="text-sm text-muted-foreground">
          Текущая цена: {{ item.effective.price ?? "Не задана" }}
          {{ item.effective.price_specification?.currency }}
        </p></template
      >
      <template v-else-if="section === 'stock'"
        ><label class="block"
          >Учёт наличия<select
            :value="stock?.manage_stock ?? 'unknown'"
            class="w-full rounded border bg-background p-2"
            @change="stockMode"
          >
            <option value="unknown">Не задано</option>
            <option value="none">Заявленный статус</option>
            <option value="own">Собственное количество</option>
            <option v-if="item.kind === 'variant'" value="parent">
              Общий источник родителя
            </option>
          </select></label
        ><label v-if="stock?.manage_stock === 'own'" class="block"
          >Количество<input
            v-model.number="stock.stock_quantity"
            type="number"
            min="0"
            step="1"
            class="w-full rounded border bg-background p-2" /></label
        ><select
          v-if="stock?.manage_stock === 'none'"
          v-model="stock.stock_status"
          aria-label="Наличие"
          class="w-full rounded border bg-background p-2"
        >
          <option value="in_stock">В наличии</option>
          <option value="out_of_stock">Нет в наличии</option>
          <option value="on_backorder">Предзаказ</option></select
        ><label v-if="stock && stock.manage_stock !== 'parent'" class="block"
          >Предзаказ<select
            v-model="stock.backorders"
            class="w-full rounded border bg-background p-2"
          >
            <option value="no">Запрещён</option>
            <option value="notify">С уведомлением</option>
            <option value="yes">Разрешён</option>
          </select></label
        >
        <p class="text-sm text-muted-foreground">
          Эффективное наличие: {{ item.stockStatus ?? "Не задано" }} · Источник:
          {{ item.effective.origins.stock?.source }}
        </p></template
      >
      <template v-else-if="section === 'measurements'"
        ><label class="block"
          >Вес (г)<select
            v-model="weight.mode"
            class="w-full rounded border bg-background p-2"
            @change="
              weight.value =
                weight.mode === 'set' ? (item.effective.weight ?? '0') : null
            "
          >
            <option v-if="item.kind === 'variant'" value="inherit">
              Наследовать
            </option>
            <option value="set">Задать</option>
            <option value="clear">Не задано</option></select
          ><input
            v-if="weight.mode === 'set'"
            v-model="weight.value"
            inputmode="decimal"
            class="mt-2 w-full rounded border bg-background p-2" /></label
        ><label class="block"
          >Размеры (мм)<select
            v-model="dimensions.mode"
            class="w-full rounded border bg-background p-2"
            @change="dimensionsMode"
          >
            <option v-if="item.kind === 'variant'" value="inherit">
              Наследовать
            </option>
            <option value="set">Задать</option>
            <option value="clear">Не задано</option>
          </select></label
        >
        <div v-if="dimensions.value" class="grid grid-cols-3 gap-2">
          <label
            v-for="field in ['length', 'width', 'height'] as const"
            :key="field"
            >{{
              field === "length"
                ? "Длина"
                : field === "width"
                  ? "Ширина"
                  : "Высота"
            }}<input
              v-model="dimensions.value[field]"
              inputmode="decimal"
              class="w-full rounded border bg-background p-2"
          /></label></div
      ></template>
      <template v-else-if="section === 'metadata'"
        ><div
          v-for="(entry, index) in metadata"
          :key="index"
          class="grid gap-2 rounded border p-3 sm:grid-cols-2"
        >
          <input
            v-model="entry.key"
            aria-label="Ключ"
            placeholder="Ключ"
            class="rounded border bg-background p-2"
          /><select
            v-model="entry.mode"
            aria-label="Режим"
            class="rounded border bg-background p-2"
          >
            <option value="set">Задать</option>
            <option v-if="item.kind === 'variant'" value="clear">
              Убрать наследуемое
            </option></select
          ><select
            v-if="entry.mode === 'set'"
            v-model="entry.value_type"
            aria-label="Тип значения"
            class="rounded border bg-background p-2"
            @change="entry.value = entry.value_type === 'boolean' ? false : ''"
          >
            <option value="text">Текст</option>
            <option value="decimal">Число</option>
            <option value="boolean">Да/Нет</option></select
          ><label v-if="entry.mode === 'set' && entry.value_type === 'boolean'"
            ><input v-model="entry.value" type="checkbox" /> Да</label
          ><input
            v-else-if="entry.mode === 'set'"
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
              mode: 'set',
            });
            mark();
          "
          >Добавить поле</Button
        >
        <p class="text-sm text-muted-foreground">
          Эффективные поля:
          {{
            item.effective.metadata
              .map((v) => `${v.key}: ${v.value}`)
              .join(", ") || "Нет"
          }}
        </p></template
      >
      <template v-else-if="section === 'attributes'"
        ><div
          v-for="(assignment, index) in assignments"
          :key="assignment.attribute_id"
          class="space-y-2 rounded border p-3"
        >
          <span>{{
            attributes.find((a) => a.id === assignment.attribute_id)?.label ??
            attributes.find((a) => a.id === assignment.attribute_id)?.code
          }}</span
          ><select
            v-model="assignment.mode"
            aria-label="Режим атрибута"
            class="ml-2 rounded border bg-background p-2"
          >
            <option value="set">Задать</option>
            <option v-if="item.kind === 'variant'" value="clear">
              Очистить
            </option></select
          ><label class="ml-2"
            ><input v-model="assignment.visible" type="checkbox" />
            Видимый</label
          >
          <div v-if="assignment.mode === 'set'" class="flex flex-wrap gap-2">
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
        <Button type="button" variant="outline" @click="addAttribute"
          >Добавить характеристику</Button
        ></template
      >
      <div class="flex gap-2">
        <Button type="submit">Сохранить</Button
        ><Button type="button" variant="outline" @click="resetFields"
          >Отмена</Button
        ><span v-if="dirty" class="self-center text-sm text-muted-foreground"
          >Есть изменения</span
        >
      </div>
    </fieldset>
  </form>
</template>
