<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { publicationStatusLabel } from "../../model/feed-publication.errors";
import type { PublicationFilters } from "../../model/feed-publication.types";
defineProps<{
  filters: PublicationFilters;
  locales: { code: string; name: string }[];
  disabled: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  status: [value: string];
  locale: [value: string];
}>();
</script>
<template>
  <div class="grid items-end gap-3 sm:grid-cols-3">
    <Field
      ><FieldLabel for="publication-search">Поиск в составе</FieldLabel
      ><Input
        id="publication-search"
        :model-value="filters.search"
        placeholder="Название или SKU"
        :disabled="disabled"
        @update:model-value="emit('search', String($event))" /></Field
    ><Field
      ><FieldLabel for="publication-status">Участие</FieldLabel
      ><Select
        :disabled="disabled"
        :model-value="filters.status || 'all'"
        @update:model-value="
          emit('status', $event === 'all' ? '' : String($event))
        "
        ><SelectTrigger id="publication-status"><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem value="all">Без архива</SelectItem
            ><SelectItem
              v-for="s in ['ENABLED', 'PAUSED', 'ARCHIVED']"
              :key="s"
              :value="s"
              >{{ publicationStatusLabel(s) }}</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    ><Field
      ><FieldLabel for="publication-locale">Язык названий</FieldLabel
      ><Select
        :disabled="disabled"
        :model-value="filters.locale"
        @update:model-value="emit('locale', String($event))"
        ><SelectTrigger id="publication-locale"><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem v-for="l in locales" :key="l.code" :value="l.code"
              >{{ l.name }} ({{ l.code }})</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    >
  </div>
</template>
