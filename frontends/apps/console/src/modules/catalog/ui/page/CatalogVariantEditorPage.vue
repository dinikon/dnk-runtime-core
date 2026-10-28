<script setup lang="ts">
import { computed, toRef } from "vue";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import ProductEditor from "../product/ProductEditor.vue";
import VariantInheritanceControls from "../product/VariantInheritanceControls.vue";
import { useProductPage } from "../../model/use-product-page";
import type { ProductSection } from "../../model/product.types";
import type { ProductStock } from "../../model/product.types";
const props = defineProps<{ variantId: string; parentStock: ProductStock }>();
const emit = defineEmits<{ close: [] }>();
const page = useProductPage(true, toRef(props, "variantId"));
const { item, contentValues, contentOverrides, blocked, pending } = page;
const sections: ProductSection[] = [
  "content",
  "status",
  "sku",
  "virtual",
  "price",
  "stock",
  "measurements",
  "galleries",
];
const errors = computed(() =>
  Object.fromEntries(sections.map((s) => [s, page.fieldError(s)])),
);
const dirty = computed(() => sections.filter(page.isDirty));
</script>
<template>
  <Sheet :open="true" @update:open="!$event && emit('close')"
    ><SheetContent
      class="flex w-full min-w-0 flex-col gap-4 overflow-y-auto sm:max-w-[min(95vw,1100px)]"
    >
      <SheetHeader
        ><SheetTitle>Редактирование варианта</SheetTitle
        ><SheetDescription
          >{{ item.data.value?.title ?? "Новая позиция" }} ·
          {{ item.data.value?.sku ?? variantId }}</SheetDescription
        ></SheetHeader
      >
      <Skeleton v-if="item.isPending.value" class="h-72 shrink-0" />
      <Alert v-if="item.isError.value" variant="destructive"
        ><AlertDescription
          >Не удалось открыть вариант.<Button
            variant="outline"
            @click="page.reload"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <template v-if="item.data.value">
        <VariantInheritanceControls
          class="mx-4"
          :item="item.data.value"
          :overrides="contentOverrides"
          :disabled="blocked || pending"
          :image-url="page.imageUrl"
          @inherit-content="page.changeContent($event, undefined)"
          @own-content="
            page.changeContent(
              $event,
              item.data.value?.effective_content?.[$event] ?? '',
            )
          "
          @clear-body="page.changeContent('body', '')"
          @gallery="
            page.save('galleries', {
              gallery:
                $event === 'inherit'
                  ? null
                  : { images: [], primary_image_id: null },
            })
          "
          @measurements="page.save('measurements', { [$event]: null })"
        />
        <ProductEditor
          class="px-4"
          :key="page.scope.value"
          :item="item.data.value"
          :parent-stock="parentStock"
          :content="contentValues"
          :disabled="blocked"
          :content-disabled="!page.schema.data.value?.schema.schema_version"
          :errors="errors"
          :dirty="dirty"
          :resets="page.resets"
          :pending="pending"
          :uploading="page.uploading.value"
          :save-status="page.saveStatus.value"
          :error="page.error.value"
          :image-url="page.imageUrl"
          @content="page.changeContent"
          @save="page.save"
          @upload="page.upload"
          @reload="page.reload"
          @retry="page.retry"
        />
      </template> </SheetContent
  ></Sheet>
</template>
