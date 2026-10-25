<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import {
  newBasketLine,
  lineTotal,
  basketPreview,
} from "../../model/sales.draft";
import type { BasketLine } from "../../model/sales.types";
const props = defineProps<{
  items: BasketLine[];
  currency: string;
  readonly?: boolean;
  savedTotal?: string;
  savedCurrency?: string;
}>();
const emit = defineEmits<{
  "update:items": [items: BasketLine[]];
  "update:currency": [currency: string];
  catalog: [];
}>();
const uid = useId(),
  nextCurrency = ref(""),
  reviewed = ref(false);
const total = computed(() => {
  try {
    return basketPreview(props.items);
  } catch {
    return "—";
  }
});
function change(index: number, key: keyof BasketLine, value: unknown) {
  emit(
    "update:items",
    props.items.map((v, i) => (i === index ? { ...v, [key]: value } : v)),
  );
}
function move(index: number, delta: number) {
  const items = [...props.items],
    target = index + delta;
  if (target < 0 || target >= items.length) return;
  [items[index], items[target]] = [items[target]!, items[index]!];
  emit("update:items", items);
}
function sum(i: BasketLine) {
  try {
    return lineTotal(i);
  } catch {
    return "Проверьте цену и количество";
  }
}
function selectCurrency(v: unknown) {
  const value = String(v);
  if (value === props.currency) return;
  if (props.items.length) {
    nextCurrency.value = value;
    reviewed.value = false;
  } else emit("update:currency", value);
}
function rename(index: number, key: string, name: string) {
  const fields = props.items[index]!.customFields;
  if (!name.trim() || (name !== key && Object.hasOwn(fields, name))) return;
  change(
    index,
    "customFields",
    Object.fromEntries(
      Object.entries(fields).map(([k, v]) => [k === key ? name : k, v]),
    ),
  );
}
</script>
<template>
  <section class="flex flex-col gap-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <Field
        ><FieldLabel :for="uid + 'currency'">Валюта продажи</FieldLabel
        ><NativeSelect
          :id="uid + 'currency'"
          :model-value="currency"
          :disabled="readonly"
          @update:model-value="selectCurrency($event)"
          ><option>USD</option>
          <option>EUR</option>
          <option>UAH</option></NativeSelect
        ></Field
      >
      <div v-if="!readonly" class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="items.length >= 200"
          @click="emit('catalog')"
          >Добавить из каталога</Button
        ><Button
          type="button"
          variant="secondary"
          :disabled="items.length >= 200"
          @click="emit('update:items', [...items, newBasketLine()])"
          >Добавить вручную</Button
        >
      </div>
    </div>
    <Empty v-if="!items.length"
      ><EmptyHeader
        ><EmptyTitle>Товары и услуги не добавлены</EmptyTitle
        ><EmptyDescription
          >Пустая корзина сохраняется с нулевой суммой в выбранной
          валюте.</EmptyDescription
        ></EmptyHeader
      ></Empty
    >
    <article
      v-for="(item, index) in items"
      :key="item.id ?? item.clientLineKey"
      class="flex flex-col gap-4 rounded-lg border p-4"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm font-medium">
          Позиция {{ index + 1 }}
          <span v-if="item.sku" class="text-muted-foreground"
            >· {{ item.sku }}</span
          >
        </p>
        <div v-if="!readonly" class="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="index === 0"
            :aria-label="'Поднять позицию ' + (index + 1)"
            @click="move(index, -1)"
            >↑</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="index === items.length - 1"
            :aria-label="'Опустить позицию ' + (index + 1)"
            @click="move(index, 1)"
            >↓</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            @click="
              emit(
                'update:items',
                items.filter((_, i) => i !== index),
              )
            "
            >Удалить</Button
          >
        </div>
      </div>
      <FieldGroup
        ><Field
          ><FieldLabel :for="uid + index + 'name'">Название *</FieldLabel
          ><Input
            :id="uid + index + 'name'"
            :model-value="item.name"
            :disabled="readonly"
            required
            maxlength="255"
            @update:model-value="change(index, 'name', String($event))"
        /></Field>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field
            ><FieldLabel :for="uid + index + 'kind'">Тип</FieldLabel
            ><NativeSelect
              :id="uid + index + 'kind'"
              :model-value="item.kind"
              :disabled="readonly || !!item.catalogItemId"
              @update:model-value="change(index, 'kind', String($event))"
              ><option value="product">Товар</option>
              <option value="service">Услуга</option></NativeSelect
            ></Field
          ><Field
            ><FieldLabel :for="uid + index + 'quantity'"
              >Количество *</FieldLabel
            ><Input
              :id="uid + index + 'quantity'"
              :model-value="item.quantity"
              inputmode="decimal"
              :disabled="readonly"
              required
              @update:model-value="
                change(index, 'quantity', String($event))
              " /></Field
          ><Field
            ><FieldLabel :for="uid + index + 'unit'">Единица *</FieldLabel
            ><Input
              :id="uid + index + 'unit'"
              :model-value="item.unit"
              :disabled="readonly"
              maxlength="32"
              @update:model-value="
                change(index, 'unit', String($event))
              " /></Field
          ><Field
            ><FieldLabel :for="uid + index + 'price'"
              >Цена, {{ props.currency }} *</FieldLabel
            ><Input
              :id="uid + index + 'price'"
              :model-value="item.unitPrice"
              inputmode="decimal"
              :disabled="readonly"
              required
              @update:model-value="change(index, 'unitPrice', String($event))"
          /></Field></div
      ></FieldGroup>
      <p class="text-sm">
        Стоимость строки: <strong>{{ sum(item) }} {{ props.currency }}</strong>
      </p>
      <details>
        <summary class="cursor-pointer text-sm">
          Дополнительные данные · {{ Object.keys(item.customFields).length }}
        </summary>
        <div class="mt-3 flex flex-col gap-2">
          <div
            v-for="(value, key) in item.customFields"
            :key="key"
            class="flex flex-wrap gap-2"
          >
            <Input
              :model-value="key"
              :aria-label="'Название дополнительного поля ' + key"
              :disabled="readonly"
              @change="
                rename(index, key, ($event.target as HTMLInputElement).value)
              "
            /><Input
              :model-value="value"
              :aria-label="'Значение ' + key"
              :disabled="readonly"
              @update:model-value="
                change(index, 'customFields', {
                  ...item.customFields,
                  [key]: String($event),
                })
              "
            /><Button
              v-if="!readonly"
              type="button"
              variant="ghost"
              @click="
                change(
                  index,
                  'customFields',
                  Object.fromEntries(
                    Object.entries(item.customFields).filter(
                      ([k]) => k !== key,
                    ),
                  ),
                )
              "
              >Убрать поле</Button
            >
          </div>
          <Button
            v-if="!readonly"
            type="button"
            variant="outline"
            @click="
              change(index, 'customFields', {
                ...item.customFields,
                ['Поле ' + (Object.keys(item.customFields).length + 1)]: '',
              })
            "
            :disabled="Object.keys(item.customFields).length >= 20"
            >Добавить поле</Button
          >
        </div>
      </details>
    </article>
    <div class="flex flex-col items-end gap-1 border-t pt-4" aria-live="polite">
      <p class="text-lg font-semibold">
        {{ readonly ? "Сумма" : "Предварительная сумма" }}: {{ total }}
        {{ props.currency }}
      </p>
      <p
        v-if="savedTotal !== undefined && !readonly"
        class="text-sm text-muted-foreground"
      >
        Сохранено на сервере: {{ savedTotal }}
        {{ savedCurrency ?? props.currency }}
      </p>
    </div>
    <Dialog :open="!!nextCurrency" @update:open="!$event && (nextCurrency = '')"
      ><DialogContent
        ><DialogHeader
          ><DialogTitle>Изменить валюту на {{ nextCurrency }}?</DialogTitle
          ><DialogDescription
            >Автоматического пересчёта по курсу нет. Проверьте и при
            необходимости измените цены всех позиций перед
            сохранением.</DialogDescription
          ></DialogHeader
        ><label class="flex items-center gap-2 text-sm"
          ><Checkbox v-model="reviewed" />Я понимаю, что цены нужно пересмотреть
          в новой валюте</label
        ><DialogFooter
          ><Button variant="outline" @click="nextCurrency = ''">Отмена</Button
          ><Button
            :disabled="!reviewed"
            @click="
              emit('update:currency', nextCurrency);
              nextCurrency = '';
            "
            >Изменить валюту</Button
          ></DialogFooter
        ></DialogContent
      ></Dialog
    >
  </section>
</template>
