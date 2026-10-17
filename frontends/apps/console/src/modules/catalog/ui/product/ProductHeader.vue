<script setup lang="ts">
import "./product.css";
import { ArrowLeft, Pencil, Eye } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
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
  <header class="flex flex-col gap-7">
    <Breadcrumb
      ><BreadcrumbList
        ><BreadcrumbItem
          ><Button variant="link" class="px-0" @click="$emit('back')"
            >Каталог</Button
          ></BreadcrumbItem
        ><BreadcrumbSeparator /><BreadcrumbItem>{{
          creating
            ? "Новый товар"
            : editing
              ? "Редактирование товара"
              : "Карточка товара"
        }}</BreadcrumbItem></BreadcrumbList
      ></Breadcrumb
    >
    <div class="flex flex-wrap items-start justify-between gap-5">
      <div class="flex min-w-0 flex-col gap-3">
        <h1
          class="break-words text-3xl font-semibold tracking-tight md:text-4xl"
        >
          {{ title }}
        </h1>
        <div
          v-if="!creating"
          class="flex flex-wrap items-center gap-3 text-sm text-muted-foreground"
        >
          <Badge variant="secondary">{{ status }}</Badge
          ><span v-if="sku">{{ sku }}</span>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <CatalogToolbar
          :locale="locale"
          :options="options"
          @locale="$emit('locale', $event)"
        /><Button
          v-if="!creating"
          :variant="editing ? 'outline' : 'default'"
          @click="$emit('mode')"
          ><Eye v-if="editing" data-icon="inline-start" /><Pencil
            v-else
            data-icon="inline-start"
          />{{ editing ? "Обзор товара" : "Редактировать" }}</Button
        ><Button v-else variant="outline" @click="$emit('back')"
          ><ArrowLeft data-icon="inline-start" />К товарам</Button
        >
      </div>
    </div>
  </header>
</template>
