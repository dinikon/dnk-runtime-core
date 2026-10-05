<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
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
import { isUuid } from "../model/forms";
const router = useRouter();
const id = ref("");
const invalid = ref(false);
function open() {
  invalid.value = !isUuid(id.value.trim());
  if (!invalid.value)
    void router.push({
      name: "catalog-product",
      params: { productId: id.value.trim() },
    });
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Товары</h1>
      <Button as-child
        ><RouterLink to="/catalog/products/new"
          >Создать товар</RouterLink
        ></Button
      >
    </header>
    <Card class="w-full max-w-2xl"
      ><CardHeader
        ><CardTitle>Открыть карточку товара</CardTitle
        ><CardDescription
          >Введите ID товара для просмотра и редактирования
          переводов.</CardDescription
        ></CardHeader
      ><CardContent
        ><form class="flex flex-col gap-5" @submit.prevent="open">
          <FieldGroup
            ><Field :data-invalid="invalid"
              ><FieldLabel for="product-id">ID товара</FieldLabel
              ><Input
                id="product-id"
                v-model="id"
                :aria-invalid="invalid"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              /><FieldDescription v-if="invalid"
                >Введите корректный UUID товара.</FieldDescription
              ></Field
            ></FieldGroup
          ><Button type="submit" class="self-start">Открыть карточку</Button>
        </form></CardContent
      ></Card
    >
  </div>
</template>
