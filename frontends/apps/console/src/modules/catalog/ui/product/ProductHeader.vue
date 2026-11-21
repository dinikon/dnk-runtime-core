<script setup lang="ts">
import "./product.css";
import { ChevronRight, Package } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LocaleOption } from "../../model/catalog.types";
defineProps<{ title: string; locale: string; options: LocaleOption[] }>();
defineEmits<{ back: []; locale: [value: string] }>();
</script>
<template>
  <div class="flex min-w-0 flex-1 items-center justify-between gap-2">
    <nav
      class="flex min-w-0 flex-1 items-center gap-1"
      aria-label="Навигация товара"
    >
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="shrink-0"
        aria-label="Товары"
        @click="$emit('back')"
        ><Package data-icon="inline-start" /><span class="hidden sm:inline"
          >Товары</span
        ></Button
      >
      <ChevronRight
        class="size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
      <span class="truncate text-sm" :title="title" aria-current="page">{{
        title
      }}</span>
    </nav>
    <FieldGroup class="w-32 shrink-0 sm:w-36"
      ><Field orientation="horizontal">
        <FieldLabel for="product-editor-locale" class="sr-only"
          >Язык товара</FieldLabel
        >
        <Select
          :model-value="locale || undefined"
          @update:model-value="$emit('locale', String($event))"
        >
          <SelectTrigger id="product-editor-locale" class="w-full"
            ><SelectValue placeholder="Язык">{{
              options.find((option) => option.code === locale)?.name ?? locale
            }}</SelectValue></SelectTrigger
          >
          <SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="option in options"
                :key="option.code"
                :value="option.code"
                >{{ option.name }} · {{ option.code }}</SelectItem
              ></SelectGroup
            ></SelectContent
          >
        </Select>
      </Field></FieldGroup
    >
  </div>
</template>
