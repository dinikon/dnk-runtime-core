<script setup lang="ts">
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
defineProps<{
  search: string;
  locale: string;
  locales: string[];
  binding?: string;
  showBindings?: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  binding: [value: string];
  locale: [value: string];
}>();
const labels: Record<string, string> = {
  uk: "Українська",
  ru: "Русский",
  en: "English",
};
</script>
<template>
  <div class="flex shrink-0 flex-col gap-3 sm:flex-row">
    <Input
      class="sm:max-w-md"
      aria-label="Поиск публикаций"
      placeholder="Название, артикул или ID площадки"
      :model-value="search"
      @update:model-value="emit('search', String($event))"
    />
    <select
      v-if="showBindings"
      class="border-input bg-background h-9 rounded-md border px-3 text-sm"
      aria-label="Связь с Catalog"
      :value="binding ?? ''"
      @change="emit('binding', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Все связи</option>
      <option value="linked">С привязкой</option>
      <option value="unlinked">Без привязки</option>
    </select>
    <Select
      v-if="locales.length > 1"
      :model-value="locale"
      @update:model-value="$event && emit('locale', String($event))"
    >
      <SelectTrigger class="sm:w-44" aria-label="Язык публикаций"
        ><SelectValue
      /></SelectTrigger>
      <SelectContent
        ><SelectGroup
          ><SelectItem
            v-for="language in locales"
            :key="language"
            :value="language"
            >{{ labels[language] ?? language }}</SelectItem
          ></SelectGroup
        ></SelectContent
      >
    </Select>
    <p v-else-if="locale" class="self-center text-sm text-muted-foreground">
      {{ labels[locale] ?? locale }}
    </p>
  </div>
</template>
