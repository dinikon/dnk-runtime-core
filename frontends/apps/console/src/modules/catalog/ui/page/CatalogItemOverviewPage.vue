<script setup lang="ts">
import { computed, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import {
  overviewModel,
  selectionLabel,
  variantRow,
} from "../../model/product-presentation";
import ProductHeader from "../product/ProductHeader.vue";
import ProductOverview from "../product/ProductOverview.vue";
import ProductVariantRow from "../product/ProductVariantRow.vue";
const {
  ctx,
  id,
  item,
  attributes,
  categories,
  tags,
  variants,
  offset,
  variant,
  variantId,
  selectVariant,
  imageUrl,
} = useProductPage(false);
watch(
  () => item.data.value,
  (v) => {
    if (v?.kind === "variant")
      void ctx.router.replace({
        path: `/catalog/items/${v.rootId}`,
        query: { ...ctx.route.query, variant: v.id },
      });
  },
  { immediate: true },
);
const selected = computed(() =>
  variantId.value && variant.data.value?.rootId === id.value
    ? variant.data.value
    : item.data.value,
);
const model = computed(() =>
  selected.value && item.data.value
    ? overviewModel(
        selected.value,
        item.data.value,
        attributes.data.value ?? [],
        categories.data.value ?? [],
        tags.data.value ?? [],
        imageUrl,
      )
    : null,
);
const rows = computed(
  () =>
    variants.data.value?.items.map((v) =>
      variantRow(v, attributes.data.value ?? [], imageUrl),
    ) ?? [],
);
function edit(child?: string) {
  void ctx.router.push({
    path: `/catalog/items/${id.value}/edit`,
    query: {
      locale: ctx.locale.value,
      ...(child ? { tab: "variants", variant: child } : {}),
    },
  });
}
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-[1440px] flex-col gap-9 p-5 md:p-8">
      <ProductHeader
        :title="model?.title ?? 'Карточка товара'"
        :kind="model?.kind"
        :status="model?.status"
        :sku="model?.sku"
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="ctx.router.push('/catalog/items')"
        @locale="ctx.selectLocale"
        @mode="edit(variantId)"
      />
      <Alert v-if="item.isError.value" variant="destructive"
        ><AlertTitle>Не удалось открыть товар</AlertTitle
        ><AlertDescription
          >{{
            getApiErrorMessage(
              item.error.value,
              "Карточка удалена или недоступна.",
            )
          }}<Button variant="outline" @click="item.refetch()"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <div
        v-if="item.isPending.value"
        class="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]"
      >
        <Skeleton class="aspect-[4/3] w-full" /><Skeleton class="h-72 w-full" />
      </div>
      <Alert v-if="variantId && variant.isError.value" variant="destructive"
        ><AlertTitle>Вариант недоступен</AlertTitle
        ><AlertDescription
          >Вариант удалён или принадлежит другому товару.<Button
            variant="outline"
            @click="selectVariant('')"
            >Вернуться к родителю</Button
          ></AlertDescription
        ></Alert
      >
      <p
        v-if="variantId && variant.isPending.value"
        role="status"
        class="text-sm text-muted-foreground"
      >
        Загружаем выбранный вариант…
      </p>
      <ProductOverview
        v-if="model && item.data.value?.kind !== 'variant'"
        :model="model"
        :variable="item.data.value?.kind === 'variable'"
        :selected-label="
          variantId && variant.data.value
            ? selectionLabel(variant.data.value, attributes.data.value ?? [])
            : undefined
        "
      />
      <section
        v-if="item.data.value?.kind === 'variable'"
        class="flex flex-col gap-5 border-t pt-8"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-semibold">Варианты</h2>
            <p class="mt-1 text-sm text-muted-foreground">
              Выберите комбинацию, чтобы посмотреть её данные.
            </p>
          </div>
          <Button v-if="variantId" variant="outline" @click="selectVariant('')"
            >Все варианты</Button
          >
        </div>
        <Alert v-if="variants.isError.value" variant="destructive"
          ><AlertTitle>Не удалось загрузить варианты</AlertTitle
          ><AlertDescription
            ><Button variant="outline" @click="variants.refetch()"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <Skeleton v-if="variants.isPending.value" class="h-24 w-full" />
        <div>
          <ProductVariantRow
            v-for="row in rows"
            :key="row.item.id"
            :row="row"
            :selected="row.item.id === variantId"
            @select="selectVariant(row.item.id)"
            @edit="edit(row.item.id)"
          />
        </div>
        <div class="flex items-center justify-end gap-3">
          <span class="text-sm text-muted-foreground"
            >{{ offset + 1 }}–{{ offset + rows.length }} из
            {{ variants.data.value?.total ?? 0 }}</span
          ><Button
            variant="outline"
            :disabled="!offset || variants.isFetching.value"
            @click="offset -= 20"
            >Назад</Button
          ><Button
            variant="outline"
            :disabled="
              offset + 20 >= (variants.data.value?.total ?? 0) ||
              variants.isFetching.value
            "
            @click="offset += 20"
            >Далее</Button
          >
        </div>
      </section>
    </div>
  </div>
</template>
