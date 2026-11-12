<script setup lang="ts">
import { InventorySkuPicker } from "@/modules/inventory";
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
      :preset="creation.preset.value"
      :disabled="!creation.ctx.active.value"
      @choose="creation.choose"
      @confirm="creation.confirm"
      @back="creation.back"
      @close="creation.close"
      @check="creation.checkCatalog"
    >
      <template #sku>
        <InventorySkuPicker
          id="create-catalog-sku"
          :search="creation.skuSearch.search.value"
          :options="creation.skuSearch.options.value"
          :loading="creation.skuSearch.loading.value"
          :error="creation.skuSearch.error.value"
          :total="creation.skuSearch.total.value"
          :selected-code="creation.skuCode.value"
          :selected-id="creation.skuId.value"
          :disabled="!creation.ctx.active.value || creation.state.uncertain"
          :pending="creation.state.pending"
          @search="creation.skuSearch.search.value = $event"
          @select="creation.selectSku"
          @create="creation.createSku"
          @clear="creation.clearSku"
          @retry="creation.skuSearch.retry"
        />
      </template>
    </ProductCreateDialog>
  </div>
</template>
