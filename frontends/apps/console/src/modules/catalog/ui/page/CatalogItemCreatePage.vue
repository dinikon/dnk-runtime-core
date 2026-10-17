<script setup lang="ts">
import { ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { catalogApi } from "../../api/catalog.api";
import { getApiErrorMessage } from "@/app/providers/http";
import { useCatalogContext } from "../../model/use-catalog-context";
import ProductHeader from "../product/ProductHeader.vue";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
const virtual = ref(false),
  dirty = ref(false),
  pending = ref(false),
  error = ref(""),
  cache = useQueryClient();
const ctx = useCatalogContext(
  () => dirty.value,
  () => pending.value,
);
async function create() {
  pending.value = true;
  error.value = "";
  const current = ctx.captureSession();
  try {
    const result = await catalogApi.createItem(virtual.value);
    if (!current()) return;
    dirty.value = false;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
    });
    pending.value = false;
    await ctx.router.push({
      path: `/catalog/items/${result.id}/edit`,
      query: { locale: ctx.locale.value },
    });
  } catch (e) {
    if (current())
      error.value = getApiErrorMessage(e, "Не удалось выполнить операцию");
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-[1440px] flex-col gap-8 p-5 md:p-8">
      <ProductHeader
        title="Новый товар"
        creating
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="ctx.router.push('/catalog/items')"
        @locale="ctx.selectLocale"
      />
      <div class="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card class="shadow-none"
          ><CardHeader
            ><CardTitle>Создание товара</CardTitle
            ><CardDescription
              >После создания черновика заполните тексты, изображения и условия
              продажи.</CardDescription
            ></CardHeader
          ><CardContent class="flex flex-col gap-6">
            <Alert v-if="error" variant="destructive"
              ><AlertTitle>Не удалось создать товар</AlertTitle
              ><AlertDescription>{{ error }}</AlertDescription></Alert
            >
            <form
              class="flex flex-col items-start gap-5"
              @submit.prevent="create()"
            >
              <label class="flex items-center gap-2 text-sm"
                ><input
                  v-model="virtual"
                  type="checkbox"
                  :disabled="pending"
                  @change="dirty = true"
                />Виртуальный товар</label
              ><Button :disabled="pending || !ctx.active.value" type="submit"
                >Создать черновик</Button
              >
            </form>
          </CardContent></Card
        >
        <aside class="flex flex-col gap-4 py-2 text-sm text-muted-foreground">
          <h2 class="font-medium text-foreground">Создание товара</h2>
          <p>
            Товар — одна продаваемая позиция с собственными ценой, артикулом и
            наличием.
          </p>
          <p>
            Черновик появится в каталоге только после нажатия «Создать
            черновик».
          </p>
        </aside>
      </div>
    </div>
  </div>
</template>
