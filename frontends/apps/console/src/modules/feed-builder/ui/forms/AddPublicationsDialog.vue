<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Field, FieldLabel } from "@/components/ui/field";
import { publicationReferenceKey } from "../../model/feed-publication.selection";
import type {
  PublicationCatalogChoice,
  PublicationChoice,
} from "../../model/feed-publication.types";
const props = defineProps<{
  open: boolean;
  products: PublicationCatalogChoice[];
  total: number;
  variants: PublicationCatalogChoice[];
  variantsTotal: number;
  selected: PublicationChoice[];
  search: string;
  offset: number;
  variantOffset: number;
  rootId: string;
  loading: boolean;
  variantsLoading: boolean;
  pending: boolean;
  allPending: boolean;
  error: string;
  sourceError: string;
  conflict: boolean;
  readonly: boolean;
}>();
const emit = defineEmits<{
  open: [value: boolean];
  search: [value: string];
  offset: [value: number];
  variantOffset: [value: number];
  root: [value: string];
  toggle: [value: PublicationChoice];
  remove: [value: PublicationChoice];
  all: [];
  submit: [];
  refresh: [];
  retry: [];
}>();
const keys = computed(
  () => new Set(props.selected.map(publicationReferenceKey)),
);
function choice(
  item: PublicationCatalogChoice,
  parent?: string,
): PublicationChoice {
  return {
    itemId: parent ?? item.id,
    variantId: parent ? item.id : null,
    title: item.title,
    sku: item.sku,
    kind: parent ? "variant" : "simple",
  };
}
const disabled = computed(
  () => props.pending || props.allPending || props.readonly || props.conflict,
);
</script>
<template>
  <Dialog :open="open" @update:open="!pending && emit('open', $event)"
    ><DialogContent
      class="flex max-h-[90dvh] flex-col overflow-y-auto sm:max-w-4xl"
      ><DialogHeader
        ><DialogTitle>Добавить товары в фид</DialogTitle
        ><DialogDescription
          >Выберите простые товары и конкретные варианты. За один раз можно
          добавить до 100 позиций.</DialogDescription
        ></DialogHeader
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <Alert v-if="conflict"
        ><AlertDescription class="flex flex-wrap items-center gap-2"
          >Настройки фида изменились. Выбор сохранён.<Button
            type="button"
            variant="outline"
            :disabled="pending || allPending"
            @click="emit('refresh')"
            >Обновить данные фида</Button
          ></AlertDescription
        ></Alert
      >
      <Alert v-if="readonly"
        ><AlertDescription
          >Фид находится в архиве. Добавление недоступно.</AlertDescription
        ></Alert
      >
      <Field
        ><FieldLabel for="publication-product-search"
          >Поиск в каталоге</FieldLabel
        ><Input
          id="publication-product-search"
          :model-value="search"
          :disabled="disabled"
          placeholder="Название или SKU"
          @update:model-value="emit('search', String($event))"
      /></Field>
      <Alert v-if="sourceError" variant="destructive"
        ><AlertDescription class="flex flex-wrap gap-2"
          >{{ sourceError
          }}<Button type="button" variant="outline" @click="emit('retry')"
            >Повторить загрузку</Button
          ></AlertDescription
        ></Alert
      >
      <div class="grid min-w-0 gap-4 md:grid-cols-2">
        <section
          class="flex min-w-0 flex-col gap-2"
          aria-label="Товары каталога"
        >
          <h3 class="font-medium">Товары каталога</h3>
          <p v-if="loading" role="status">Загрузка товаров…</p>
          <p v-else-if="!products.length" class="text-sm text-muted-foreground">
            Товары не найдены.
          </p>
          <div
            v-for="item in products"
            :key="item.id"
            class="flex min-w-0 items-start gap-3 rounded border p-3"
          >
            <Checkbox
              v-if="item.kind === 'simple'"
              :model-value="keys.has(publicationReferenceKey(choice(item)))"
              :disabled="disabled || !item.available"
              :aria-label="`Выбрать ${item.title} ${item.sku ?? ''}`"
              @update:model-value="emit('toggle', choice(item))"
            />
            <div class="min-w-0 flex-1">
              <p class="break-words text-sm font-medium">{{ item.title }}</p>
              <p class="break-words text-xs text-muted-foreground">
                {{ item.sku }} ·
                {{
                  item.kind === "variable"
                    ? "Вариативный товар"
                    : "Простой товар"
                }}{{ !item.available ? " · В архиве" : "" }}
              </p>
            </div>
            <Button
              v-if="item.kind === 'variable'"
              type="button"
              variant="outline"
              size="sm"
              :disabled="disabled || !item.available"
              :aria-label="`Варианты ${item.sku ?? item.title}`"
              @click="emit('root', item.id)"
              >Варианты</Button
            >
          </div>
          <div class="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              :disabled="disabled || loading || offset === 0"
              @click="emit('offset', Math.max(0, offset - 20))"
              >Назад</Button
            ><Button
              type="button"
              variant="outline"
              :disabled="disabled || loading || offset + 20 >= total"
              @click="emit('offset', offset + 20)"
              >Далее</Button
            >
          </div>
        </section>
        <section
          class="flex min-w-0 flex-col gap-2"
          aria-label="Варианты товара"
        >
          <h3 class="font-medium">Варианты товара</h3>
          <p v-if="!rootId" class="text-sm text-muted-foreground">
            Откройте вариативный товар, чтобы выбрать его варианты.
          </p>
          <template v-else
            ><Button
              type="button"
              variant="outline"
              :disabled="disabled || allPending"
              @click="emit('all')"
              >{{
                allPending
                  ? "Получаем текущий список…"
                  : "Все существующие варианты"
              }}</Button
            >
            <p class="text-xs text-muted-foreground">
              Фиксируем выбранный набор. Новые варианты не добавляются
              автоматически.
            </p>
            <p v-if="variantsLoading" role="status">Загрузка вариантов…</p>
            <p v-else-if="!variants.length">Варианты не найдены.</p>
            <div
              v-for="item in variants"
              :key="item.id"
              class="flex min-w-0 items-start gap-3 rounded border p-3"
            >
              <Checkbox
                :model-value="
                  keys.has(publicationReferenceKey(choice(item, rootId)))
                "
                :disabled="disabled || !item.available"
                :aria-label="`Выбрать вариант ${item.sku ?? item.id}`"
                @update:model-value="emit('toggle', choice(item, rootId))"
              />
              <div class="min-w-0">
                <p class="break-words text-sm">{{ item.title }}</p>
                <p class="break-words text-xs text-muted-foreground">
                  {{ item.sku ?? `Без SKU · ${item.id.slice(0, 8)}`
                  }}{{ !item.available ? " · В архиве" : "" }}
                </p>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
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
                  disabled ||
                  variantsLoading ||
                  variantOffset + 20 >= variantsTotal
                "
                @click="emit('variantOffset', variantOffset + 20)"
                >Следующие варианты</Button
              >
            </div></template
          >
        </section>
      </div>
      <section
        v-if="selected.length"
        class="flex flex-col gap-2 border-t pt-3"
        aria-label="Выбранные позиции"
      >
        <strong>Выбрано {{ selected.length }} из 100</strong>
        <div
          v-for="item in selected"
          :key="publicationReferenceKey(item)"
          class="flex items-center justify-between gap-2 text-sm"
        >
          <span class="min-w-0 break-words"
            >{{ item.title }} ·
            {{ item.sku ?? item.variantId ?? item.itemId }}</span
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="pending || allPending"
            :aria-label="`Убрать из выбора ${item.sku ?? item.title}`"
            @click="emit('remove', item)"
            >Убрать</Button
          >
        </div>
      </section>
      <DialogFooter
        ><Button
          type="button"
          variant="outline"
          :disabled="pending || allPending"
          @click="emit('open', false)"
          >Отмена</Button
        ><Button
          type="button"
          :disabled="disabled || allPending || !selected.length"
          @click="emit('submit')"
          >{{
            pending ? "Добавляем…" : `Добавить выбранные (${selected.length})`
          }}</Button
        ></DialogFooter
      >
    </DialogContent></Dialog
  >
</template>
