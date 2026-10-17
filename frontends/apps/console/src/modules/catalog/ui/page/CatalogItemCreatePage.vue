<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { catalogApi } from "../../api/catalog.api";
import { getApiErrorMessage } from "@/app/providers/http";
import { useCatalogContext } from "../../model/use-catalog-context";
import { loadAttributes } from "../../model/catalog-options";
import type { StructureDTO } from "../../api/catalog.dto";
import CatalogItemStructureForm from "../forms/CatalogItemStructureForm.vue";
import ProductHeader from "../product/ProductHeader.vue";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
const kind = ref("simple"),
  virtual = ref(false),
  dirty = ref(false),
  pending = ref(false),
  error = ref(""),
  cache = useQueryClient();
const ctx = useCatalogContext(
  () => dirty.value,
  () => pending.value,
);
const attributes = useQuery({
  queryKey: computed(() => ctx.key("attribute-options")),
  enabled: computed(
    () =>
      !!ctx.locale.value && !!ctx.tenantId.value && kind.value === "variable",
  ),
  queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
});
async function create(structure?: StructureDTO) {
  pending.value = true;
  error.value = "";
  const current = ctx.captureSession();
  try {
    const result = structure
      ? await catalogApi.createVariable(structure)
      : await catalogApi.createSimple(virtual.value);
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
              >Выберите вид товара. После создания черновика заполните тексты,
              изображения и условия продажи.</CardDescription
            ></CardHeader
          ><CardContent class="flex flex-col gap-6">
            <FieldGroup
              ><Field
                ><FieldLabel for="product-kind">Вид товара</FieldLabel
                ><select
                  id="product-kind"
                  v-model="kind"
                  :disabled="pending"
                  class="w-full rounded-md border bg-background p-2"
                  @change="dirty = true"
                >
                  <option value="simple">Простой товар</option>
                  <option value="variable">Товар с вариантами</option>
                </select></Field
              ></FieldGroup
            >
            <Alert
              v-if="error || attributes.isError.value"
              variant="destructive"
              ><AlertTitle>Не удалось создать товар</AlertTitle
              ><AlertDescription>{{
                error ||
                getApiErrorMessage(
                  attributes.error.value,
                  "Не удалось загрузить характеристики.",
                )
              }}</AlertDescription></Alert
            >
            <form
              v-show="kind === 'simple'"
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
            <CatalogItemStructureForm
              v-if="kind === 'variable'"
              :initial="null"
              :attributes="attributes.data.value ?? []"
              :pending="
                pending || !ctx.active.value || attributes.isPending.value
              "
              :reset="0"
              submit-label="Создать черновик"
              @dirty="dirty = $event"
              @submit="create"
            /> </CardContent
        ></Card>
        <aside class="flex flex-col gap-4 py-2 text-sm text-muted-foreground">
          <h2 class="font-medium text-foreground">Какой вид выбрать</h2>
          <p>
            Простой товар — одна продаваемая позиция с собственными ценой и
            наличием.
          </p>
          <p>
            Товар с вариантами — несколько комбинаций характеристик, например
            размер и цвет. У каждого варианта свои цена и артикул.
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
