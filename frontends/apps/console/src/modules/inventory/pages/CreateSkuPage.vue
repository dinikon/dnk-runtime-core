<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { inventoryApi } from "../api/inventory.api";
import { skuKeys, useInventoryTenant } from "../model/queries";
import { inventoryError, validSkuCode, validSkuTitle } from "../model/forms";
import RequestError from "../ui/RequestError.vue";
const router = useRouter();
const client = useQueryClient();
const tenant = useInventoryTenant();
const code = ref("");
const title = ref("");
const submitted = ref(false);
const succeeded = ref(false);
const pending = ref(false);
const dirty = computed(() => !succeeded.value && !!(code.value || title.value));
const mutation = useMutation({
  mutationFn: inventoryApi.createSku,
  retry: false,
});
useUnsavedChanges(dirty, pending);
async function submit() {
  if (pending.value) return;
  submitted.value = true;
  if (!validSkuCode(code.value) || !validSkuTitle(title.value)) return;
  pending.value = true;
  try {
    const sku = await mutation.mutateAsync({
      code: code.value.trim(),
      title: title.value.trim(),
    });
    client.setQueryData(skuKeys.detail(tenant.value, sku.id), sku);
    await client.invalidateQueries({ queryKey: skuKeys.list(tenant.value) });
    succeeded.value = true;
    pending.value = false;
    await router.push({ name: "inventory-sku", params: { skuId: sku.id } });
  } catch {
    /* Preserve form; mutation state displays server errors. */
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Создать SKU</h1>
      <Button variant="outline" as-child
        ><RouterLink to="/inventory/skus">К списку SKU</RouterLink></Button
      >
    </header>
    <Card class="w-full max-w-2xl"
      ><CardHeader
        ><CardTitle>Новая учётная единица</CardTitle
        ><CardDescription
          >Код и учётное название SKU не зависят от переводов карточки
          товара.</CardDescription
        ></CardHeader
      ><CardContent
        ><form class="flex flex-col gap-5" @submit.prevent="submit">
          <FieldGroup
            ><Field :data-invalid="submitted && !validSkuCode(code)"
              ><FieldLabel for="sku-code">Код</FieldLabel
              ><Input
                id="sku-code"
                v-model="code"
                :disabled="pending"
                :aria-invalid="submitted && !validSkuCode(code)"
              /><FieldDescription
                >От 1 до 128 символов без управляющих символов. Регистр и
                внутренние пробелы сохраняются.</FieldDescription
              >
              <p
                v-if="submitted && !validSkuCode(code)"
                role="alert"
                class="text-sm text-destructive"
              >
                Введите корректный код SKU.
              </p></Field
            ><Field :data-invalid="submitted && !validSkuTitle(title)"
              ><FieldLabel for="sku-title">Название</FieldLabel
              ><Input
                id="sku-title"
                v-model="title"
                :disabled="pending"
                :aria-invalid="submitted && !validSkuTitle(title)"
              /><FieldDescription
                >От 1 до 255 символов после удаления пробелов по
                краям.</FieldDescription
              >
              <p
                v-if="submitted && !validSkuTitle(title)"
                role="alert"
                class="text-sm text-destructive"
              >
                Введите корректное название SKU.
              </p></Field
            ></FieldGroup
          ><RequestError
            v-if="mutation.isError.value"
            :message="inventoryError(mutation.error.value)"
          /><Button type="submit" class="self-start" :disabled="pending">{{
            pending ? "Создание…" : "Создать SKU"
          }}</Button>
        </form></CardContent
      ></Card
    >
  </div>
</template>
