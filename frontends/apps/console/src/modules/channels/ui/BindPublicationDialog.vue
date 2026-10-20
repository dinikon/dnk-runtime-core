<script setup lang="ts">
import { ref } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  CatalogCandidatesPage,
  CatalogCandidate,
} from "../model/catalog-links.types";
import type { ReferenceOption } from "../model/channels.types";
import { reasonLabel } from "../model/channels.presentation";
import ChannelsQueryBody from "./ChannelsQueryBody.vue";
import ChannelsPagination from "./ChannelsPagination.vue";
defineProps<{
  title: string;
  items: CatalogCandidatesPage | undefined;
  locale: string;
  locales: ReferenceOption[];
  page: number;
  loading: boolean;
  pending: boolean;
  error: string | null;
  actionError: string | null;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  locale: [value: string];
  page: [value: number];
  retry: [];
  bind: [item: CatalogCandidate];
}>();
const search = ref("");
function submitSearch(): void {
  emit("search", search.value.trim());
}
</script>
<template>
  <Dialog
    :open="true"
    @update:open="
      (value) => {
        if (!value && !pending) emit('close');
      }
    "
    ><DialogContent
      class="w-[calc(100vw_-_2rem)] max-h-[90svh] overflow-auto sm:max-w-3xl"
      :show-close-button="!pending"
      @escape-key-down="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      @interact-outside="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      ><DialogHeader
        ><DialogTitle>Связать с товаром</DialogTitle
        ><DialogDescription
          >{{ title }} · Связь не изменяет название, SKU, цену или наличие
          товара.</DialogDescription
        ></DialogHeader
      >
      <form
        class="flex flex-wrap items-end gap-3"
        @submit.prevent="submitSearch"
      >
        <FieldGroup class="flex flex-1 flex-col gap-3 sm:flex-row"
          ><Field
            ><FieldLabel for="bind-search">Название или SKU товара</FieldLabel
            ><Input
              id="bind-search"
              v-model="search"
              maxlength="200"
              :disabled="pending" /></Field
          ><Field class="sm:w-auto"
            ><FieldLabel for="bind-locale">Язык поиска</FieldLabel
            ><NativeSelect
              id="bind-locale"
              :model-value="locale"
              :disabled="pending"
              @update:model-value="(value) => emit('locale', String(value))"
              ><NativeSelectOption value="" disabled
                >Выберите язык</NativeSelectOption
              ><NativeSelectOption
                v-for="option in locales"
                :key="option.code"
                :value="option.code"
                >{{ option.name }}</NativeSelectOption
              ></NativeSelect
            ></Field
          ></FieldGroup
        ><Button type="submit" variant="outline" :disabled="pending"
          >Найти товары</Button
        >
      </form>
      <Alert v-if="actionError" variant="destructive"
        ><AlertDescription>{{ actionError }}</AlertDescription></Alert
      ><ChannelsQueryBody
        :pending="loading"
        :error="error"
        :has-data="!!items"
        :empty="!items?.items.length"
        empty-title="Товары не найдены"
        empty-description="Измените запрос или создайте Draft из публикации."
        @retry="emit('retry')"
        ><Table
          ><TableHeader
            ><TableRow
              ><TableHead>Товар</TableHead><TableHead>SKU</TableHead
              ><TableHead>Статус</TableHead
              ><TableHead>Действие</TableHead></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-for="item in items?.items ?? []" :key="item.id"
              ><TableCell class="max-w-64 whitespace-normal">{{
                item.title ?? "Без названия"
              }}</TableCell
              ><TableCell>{{ item.sku ?? "—" }}</TableCell
              ><TableCell>{{
                item.status === "draft"
                  ? "Draft"
                  : item.status === "active"
                    ? "Активен"
                    : item.status === "archived"
                      ? "Архив"
                      : item.status
              }}</TableCell
              ><TableCell
                ><Button
                  size="sm"
                  :disabled="pending || loading || !item.canBind"
                  @click="emit('bind', item)"
                  >{{ pending ? "Связываем…" : "Связать" }}</Button
                >
                <p
                  v-if="item.reasonCode"
                  class="text-muted-foreground mt-1 max-w-56 whitespace-normal text-xs"
                >
                  {{ reasonLabel(item.reasonCode) }}
                </p></TableCell
              ></TableRow
            ></TableBody
          ></Table
        ></ChannelsQueryBody
      ><ChannelsPagination
        v-if="items"
        :page="page"
        :total="items.total"
        :limit="20"
        :pending="pending || loading"
        @change="(value) => emit('page', value)" /></DialogContent
  ></Dialog>
</template>
