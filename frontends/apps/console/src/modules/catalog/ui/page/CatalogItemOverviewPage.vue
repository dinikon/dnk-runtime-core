<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import { overviewModel } from "../../model/product-presentation";
import ProductHeader from "../product/ProductHeader.vue";
import ProductOverview from "../product/ProductOverview.vue";
const { ctx, id, item, attributes, categories, tags, imageUrl } =
  useProductPage(false);
const model = computed(() =>
  item.data.value
    ? overviewModel(
        item.data.value,
        attributes.data.value ?? [],
        categories.data.value ?? [],
        tags.data.value ?? [],
        imageUrl,
      )
    : null,
);
function edit() {
  void ctx.router.push({
    path: `/catalog/items/${id.value}/edit`,
    query: { locale: ctx.locale.value },
  });
}
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-[1440px] flex-col gap-9 p-5 md:p-8">
      <ProductHeader
        :title="model?.title ?? 'Карточка товара'"
        :status="model?.status"
        :sku="model?.sku"
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="ctx.router.push('/catalog/items')"
        @locale="ctx.selectLocale"
        @mode="edit"
      />
      <Alert v-if="item.isError.value" variant="destructive">
        <AlertTitle>Не удалось открыть товар</AlertTitle>
        <AlertDescription
          >{{
            getApiErrorMessage(
              item.error.value,
              "Карточка удалена или недоступна.",
            )
          }}<Button variant="outline" @click="item.refetch()"
            >Повторить</Button
          ></AlertDescription
        >
      </Alert>
      <div
        v-if="item.isPending.value"
        class="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]"
      >
        <Skeleton class="aspect-[4/3] w-full" /><Skeleton class="h-72 w-full" />
      </div>
      <ProductOverview v-if="model" :model="model" />
    </div>
  </div>
</template>
