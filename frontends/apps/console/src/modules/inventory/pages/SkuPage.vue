<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useSku } from "../model/queries";
import { inventoryError } from "../model/forms";
import RequestError from "../ui/RequestError.vue";
const route = useRoute();
const id = computed(() => String(route.params.skuId ?? ""));
const sku = useSku(id);
const formatDate = (value: string) => new Date(value).toLocaleString("ru-RU");
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Карточка SKU</h1>
      <Button variant="outline" as-child
        ><RouterLink to="/inventory/skus">К списку SKU</RouterLink></Button
      >
    </header>
    <Skeleton
      v-if="sku.isPending.value"
      class="h-48"
      aria-label="Загрузка SKU"
    /><RequestError
      v-if="sku.isError.value"
      :message="inventoryError(sku.error.value)"
      retry
      :pending="sku.isFetching.value"
      @retry="sku.refetch()"
    /><Card v-else-if="sku.data.value" class="w-full max-w-3xl"
      ><CardHeader
        ><CardTitle class="break-all">{{ sku.data.value.code }}</CardTitle
        ><CardDescription class="break-words">{{
          sku.data.value.title
        }}</CardDescription></CardHeader
      ><CardContent class="flex flex-col gap-6"
        ><dl class="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt class="text-muted-foreground">ID</dt>
            <dd class="break-all">{{ sku.data.value.id }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">Создан</dt>
            <dd>{{ formatDate(sku.data.value.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">Обновлён</dt>
            <dd>{{ formatDate(sku.data.value.updated_at) }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">Создал</dt>
            <dd class="break-all">{{ sku.data.value.created_by }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">Обновил</dt>
            <dd class="break-all">{{ sku.data.value.updated_by }}</dd>
          </div>
        </dl>
      </CardContent></Card
    >
  </div>
</template>
