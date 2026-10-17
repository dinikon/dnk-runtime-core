<script setup lang="ts">
import "../product/product.css";
import { Button } from "@/components/ui/button";
import { useCreateCatalogItem } from "../../model/use-create-catalog-item";
import ProductCreateDialog from "../product/ProductCreateDialog.vue";
const creation = useCreateCatalogItem(true);
</script>
<template>
  <div class="product-editor min-h-0 min-w-0 flex-1 overflow-y-auto p-4 md:p-8">
    <Button variant="ghost" @click="creation.close">Вернуться в каталог</Button>
    <ProductCreateDialog
      :open="creation.open.value"
      :state="creation.state"
      :disabled="!creation.ctx.active.value"
      @choose="creation.choose"
      @close="creation.close"
      @check="creation.checkCatalog"
    />
  </div>
</template>
