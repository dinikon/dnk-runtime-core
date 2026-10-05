<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import type { CategoryListDto } from "../api/contracts";
import { categoryLabel } from "../model/categories";
import CategoryTree from "./CategoryTree.vue";
import RequestError from "./RequestError.vue";
const props = defineProps<{
  items: CategoryListDto[];
  locale: string;
  pending: boolean;
  loading: boolean;
  loadError: string;
  error: string;
  dirty: boolean;
  available: boolean;
}>();
defineEmits<{ save: []; retry: [] }>();
const selected = defineModel<string[]>("selected", { required: true });
const primary = defineModel<string | null>("primary", { required: true });
const selectedItems = computed(() =>
  selected.value.map(
    (id) =>
      props.items.find((item) => item.id === id) ?? {
        id,
        parent_id: null,
        name: null,
      },
  ),
);
function toggle(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((value) => value !== id)
    : [...selected.value, id];
  if (primary.value && !selected.value.includes(primary.value))
    primary.value = null;
}
</script>
<template>
  <Card class="w-full max-w-3xl"
    ><CardHeader
      ><CardTitle>Категории товара</CardTitle
      ><CardDescription
        >Назначьте категории и выберите основную. Сохранение заменяет весь
        набор.</CardDescription
      ></CardHeader
    ><CardContent
      ><form class="flex flex-col gap-5" @submit.prevent="$emit('save')">
        <Skeleton
          v-if="loading"
          class="h-24"
          aria-label="Загрузка категорий"
        /><RequestError
          v-if="loadError"
          :message="loadError"
          retry
          @retry="$emit('retry')"
        /><CategoryTree
          v-if="available && items.length"
          :items="items"
          :locale="locale"
          selectable
          :selected="selected"
          :disabled="pending"
          @toggle="toggle"
        />
        <p v-else-if="available" class="text-sm text-muted-foreground">
          Категорий пока нет.
        </p>
        <FieldGroup
          ><Field
            ><FieldLabel for="primary-category">Основная категория</FieldLabel
            ><Select
              :model-value="primary ?? '__none__'"
              :disabled="pending || !selected.length || !available"
              @update:model-value="
                (value) => {
                  if (value)
                    primary =
                      String(value) === '__none__' ? null : String(value);
                }
              "
              ><SelectTrigger id="primary-category" class="w-full"
                ><SelectValue>{{
                  primary
                    ? categoryLabel(
                        selectedItems.find((item) => item.id === primary) ?? {
                          id: primary,
                          name: null,
                        },
                      )
                    : "Не выбрана"
                }}</SelectValue></SelectTrigger
              ><SelectContent
                ><SelectGroup
                  ><SelectItem value="__none__">Не выбрана</SelectItem
                  ><SelectItem
                    v-for="item in selectedItems"
                    :key="item.id"
                    :value="item.id"
                    >{{ categoryLabel(item) }}</SelectItem
                  ></SelectGroup
                ></SelectContent
              ></Select
            ></Field
          ></FieldGroup
        ><RequestError v-if="error" :message="error" /><Button
          type="submit"
          class="self-start"
          :disabled="pending || !dirty || !available"
          >{{ pending ? "Сохранение…" : "Сохранить категории" }}</Button
        >
      </form></CardContent
    ></Card
  >
</template>
