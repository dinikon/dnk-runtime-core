<script setup lang="ts">
import "./product.css";
import { ArrowLeft, Pencil, Eye } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import CatalogToolbar from "../CatalogToolbar.vue";
import type { LocaleOption } from "../../model/catalog.types";
defineProps<{
  title: string;
  status?: string;
  sku?: string | null;
  editing?: boolean;
  creating?: boolean;
  locale: string;
  options: LocaleOption[];
}>();
defineEmits<{ back: []; mode: []; locale: [value: string] }>();
</script>
<template>
  <header class="flex min-w-0 flex-col gap-4">
    <nav aria-label="Назад к каталогу">
      <Button variant="ghost" class="min-h-11 -ml-3" @click="$emit('back')"
        ><ArrowLeft data-icon="inline-start" />Каталог</Button
      >
    </nav>
    <div class="flex min-w-0 flex-wrap items-start justify-between gap-4">
      <div class="flex min-w-0 flex-1 flex-col gap-2">
        <h1
          class="break-words text-2xl font-semibold tracking-tight md:text-3xl"
        >
          {{ editing ? "Редактирование товара" : title }}
        </h1>
        <div
          v-if="!editing && !creating"
          class="flex flex-wrap items-center gap-3 text-sm text-muted-foreground"
        >
          <Badge v-if="status" variant="secondary">{{ status }}</Badge
          ><span v-if="sku" class="break-all">{{ sku }}</span>
        </div>
      </div>
      <div class="flex w-full min-w-0 flex-wrap items-center gap-3 sm:w-auto">
        <CatalogToolbar
          class="min-w-0 flex-1 sm:flex-none"
          :locale="locale"
          :options="options"
          @locale="$emit('locale', $event)"
        /><Button
          v-if="!creating"
          :variant="editing ? 'outline' : 'default'"
          class="min-h-11"
          :aria-label="editing ? 'Обзор товара' : 'Редактировать'"
          @click="$emit('mode')"
          ><Eye v-if="editing" data-icon="inline-start" /><Pencil
            v-else
            data-icon="inline-start"
          /><span class="hidden sm:inline">{{
            editing ? "Обзор товара" : "Редактировать"
          }}</span></Button
        >
      </div>
    </div>
  </header>
</template>
