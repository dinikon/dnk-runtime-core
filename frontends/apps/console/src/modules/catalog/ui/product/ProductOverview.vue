<script setup lang="ts">
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Check, CircleMinus } from "@lucide/vue";
import ProductMedia from "./ProductMedia.vue";
import type { ProductOverviewModel } from "../../model/product.types";
defineProps<{
  model: ProductOverviewModel;
}>();
</script>
<template>
  <div class="grid min-w-0 gap-8 xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-10">
    <div class="flex min-w-0 flex-col gap-8">
      <ProductMedia :images="model.images" :primary="model.primaryImage" />
      <section class="flex flex-col gap-4">
        <h2 class="text-lg font-semibold">О товаре</h2>
        <!-- HTML очищается в модели представления через DOMPurify. -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-if="model.body" class="product-prose" v-html="model.body" />
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
    </div>
    <aside class="flex min-w-0 flex-col gap-5">
      <Card class="shadow-none"
        ><CardHeader><CardTitle>Цена</CardTitle></CardHeader
        ><CardContent class="flex flex-col gap-3"
          ><p class="break-words text-3xl font-semibold tracking-tight">
            {{ model.price }}
          </p>
        </CardContent></Card
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
          <template v-if="model.quantity !== null"
            ><Separator />
            <div>
              <p class="text-xs uppercase tracking-wider text-muted-foreground">
                Количество
              </p>
              <p class="mt-2 text-3xl font-semibold">
                {{ model.quantity }}
              </p>
            </div>
          </template></CardContent
        ></Card
      >
    </aside>
  </div>
</template>
