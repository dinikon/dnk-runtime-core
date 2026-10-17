<script setup lang="ts">
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Check, CircleMinus } from "@lucide/vue";
import ProductMedia from "./ProductMedia.vue";
import type { ProductOverviewModel } from "../../model/product.types";
defineProps<{
  model: ProductOverviewModel;
  variable: boolean;
  selectedLabel?: string;
}>();
</script>
<template>
  <div class="grid min-w-0 gap-8 xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-10">
    <div class="flex min-w-0 flex-col gap-8">
      <p v-if="selectedLabel" class="text-sm text-muted-foreground">
        Выбранный вариант:
        <span class="font-medium text-foreground">{{ selectedLabel }}</span>
      </p>
      <ProductMedia :images="model.images" :primary="model.primaryImage" />
      <section class="flex flex-col gap-4">
        <h2 class="text-lg font-semibold">О товаре</h2>
        <!-- HTML очищается в модели представления через DOMPurify. -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          v-if="model.descriptions.short"
          class="product-prose"
          v-html="model.descriptions.short"
        />
        <p v-else class="text-sm text-muted-foreground">
          Краткое описание: Не задано
        </p>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          v-if="model.descriptions.full"
          class="product-prose"
          v-html="model.descriptions.full"
        />
        <p v-else class="text-sm text-muted-foreground">Описание: Не задано</p>
      </section>
      <Separator />
      <section class="flex flex-col gap-5">
        <h2 class="text-lg font-semibold">Вес и размеры</h2>
        <dl class="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <div
            v-for="measurement in model.measurements"
            :key="measurement.label"
          >
            <dt
              class="text-xs font-medium uppercase tracking-wider text-muted-foreground"
            >
              {{ measurement.label }}
            </dt>
            <dd class="mt-2 text-sm">{{ measurement.value }}</dd>
          </div>
        </dl>
      </section>
      <Separator />
      <section class="flex flex-col gap-4">
        <h2 class="text-lg font-semibold">Характеристики</h2>
        <dl v-if="model.attributes.length" class="grid gap-5 sm:grid-cols-2">
          <div v-for="attribute in model.attributes" :key="attribute.label">
            <dt class="text-sm text-muted-foreground">{{ attribute.label }}</dt>
            <dd class="mt-1 text-sm font-medium">{{ attribute.value }}</dd>
          </div>
        </dl>
        <p v-else class="text-sm text-muted-foreground">Не задано</p>
      </section>
      <section v-if="!variable" class="flex flex-col gap-4">
        <Separator />
        <h2 class="text-lg font-semibold">Категории и метки</h2>
        <div class="flex flex-wrap gap-2">
          <Badge
            v-for="category in model.categories"
            :key="category"
            variant="secondary"
            >{{ category }}</Badge
          ><Badge v-for="tag in model.tags" :key="tag" variant="outline">{{
            tag
          }}</Badge
          ><span
            v-if="!model.categories.length && !model.tags.length"
            class="text-sm text-muted-foreground"
            >Не задано</span
          >
        </div>
      </section>
    </div>
    <aside class="flex min-w-0 flex-col gap-5">
      <Card class="shadow-none"
        ><CardHeader
          ><CardTitle>{{
            variable && !selectedLabel ? "Диапазон цен" : "Цена"
          }}</CardTitle></CardHeader
        ><CardContent class="flex flex-col gap-3"
          ><p class="break-words text-3xl font-semibold tracking-tight">
            {{ model.price }}
          </p>
          <p v-if="model.priceIncomplete" class="text-sm text-muted-foreground">
            Не у всех активных вариантов задана цена.
          </p></CardContent
        ></Card
      >
      <Card class="shadow-none"
        ><CardHeader><CardTitle>Наличие и продажа</CardTitle></CardHeader
        ><CardContent class="flex flex-col gap-5"
          ><p class="text-xl font-medium">{{ model.stock }}</p>
          <div class="flex items-start gap-2 text-sm">
            <Check
              v-if="model.available"
              class="mt-0.5 size-4 shrink-0"
            /><CircleMinus v-else class="mt-0.5 size-4 shrink-0" /><span>{{
              model.available
                ? "Доступен для продажи"
                : "Недоступен для продажи"
            }}</span>
          </div>
          <p v-if="model.sharedSource" class="text-sm text-muted-foreground">
            Использует общий остаток родителя.
          </p>
          <template v-if="model.sharedQuantity !== null"
            ><Separator />
            <div>
              <p class="text-xs uppercase tracking-wider text-muted-foreground">
                {{ variable ? "Общий запас семьи" : "Количество" }}
              </p>
              <p class="mt-2 text-3xl font-semibold">
                {{ model.sharedQuantity }}
              </p>
            </div>
            <p v-if="variable" class="text-sm text-muted-foreground">
              Для вариантов без собственного учёта количества.
            </p></template
          ></CardContent
        ></Card
      >
    </aside>
  </div>
</template>
