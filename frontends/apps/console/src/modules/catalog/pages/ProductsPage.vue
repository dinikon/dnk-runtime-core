<script setup lang="ts">
import { computed, ref } from "vue";
import { useUserStore } from "@/app/stores/user";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocales, useProducts } from "../model/queries";
import { catalogError } from "../model/forms";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";

const user = useUserStore();
const locales = useLocales();
const selectedLocale = ref("");
const language = computed(
  () => selectedLocale.value || user.user?.interface_language || "uk",
);
const products = useProducts(language);
const options = computed(() =>
  (locales.data.value ?? []).map((item) => ({
    code: item.code,
    name: item.name,
  })),
);
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Товары</h1>
        <p class="text-sm text-muted-foreground">
          Карточки и продаваемые варианты каталога
        </p>
      </div>
      <Button as-child
        ><RouterLink to="/catalog/products/new"
          >Создать товар</RouterLink
        ></Button
      >
    </header>
    <Card>
      <CardHeader class="flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle>Каталог</CardTitle
          ><CardDescription
            >Название показано только для выбранного языка.</CardDescription
          >
        </div>
        <div class="w-56">
          <LocaleSelect
            :options="options"
            :value="language"
            @change="selectedLocale = $event"
          />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton
          v-if="products.isPending.value"
          class="h-48"
          aria-label="Загрузка товаров"
        />
        <RequestError
          v-else-if="products.isError.value"
          :message="catalogError(products.error.value)"
          retry
          :pending="products.isFetching.value"
          @retry="products.refetch()"
        />
        <p
          v-else-if="!products.data.value?.length"
          class="py-8 text-center text-sm text-muted-foreground"
        >
          Товаров пока нет. Создайте первую карточку.
        </p>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="border-b text-muted-foreground">
              <tr>
                <th class="p-3 font-medium">Товар</th>
                <th class="p-3 font-medium">Вид</th>
                <th class="p-3 font-medium">Варианты</th>
                <th class="p-3 font-medium">Основная категория</th>
                <th class="p-3 font-medium">Обновлён</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in products.data.value"
                :key="item.id"
                class="border-b last:border-0 hover:bg-muted/40"
              >
                <td class="p-3">
                  <RouterLink
                    class="font-medium hover:underline"
                    :to="{
                      name: 'catalog-product',
                      params: { productId: item.id },
                      query: { locale: language },
                    }"
                    >{{ item.name ?? "Без перевода" }}</RouterLink
                  >
                  <div class="text-xs text-muted-foreground">{{ item.id }}</div>
                </td>
                <td class="p-3">
                  {{ item.kind === "simple" ? "Простой" : "Вариативный" }}
                </td>
                <td class="p-3">{{ item.variant_count }}</td>
                <td class="p-3">{{ item.primary_category_name ?? "—" }}</td>
                <td class="p-3">
                  {{ new Date(item.updated_at).toLocaleDateString() }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
