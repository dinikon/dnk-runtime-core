<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { usePublication } from "../model/queries";
import { sourceLabel, priceLabel, dateLabel } from "../model/publications";
const route = useRoute();
const id = computed(() => String(route.params.channelId ?? "")),
  publicationId = computed(() => String(route.params.publicationId ?? ""));
const publication = usePublication(id, publicationId),
  item = publication.data;
const incomplete = computed(
  () =>
    item.value?.expected_variations != null &&
    item.value.variants.length < item.value.expected_variations,
);
const typeLabels: Record<string, string> = {
  simple: "Простой",
  variable: "С вариациями",
  grouped: "Групповой",
  external: "Внешний",
  retail: "Розничный",
  wholesale: "Оптовый",
  universal: "Розница и опт",
};
</script>
<template>
  <div class="flex flex-col gap-5">
    <div>
      <Button as-child variant="outline"
        ><RouterLink :to="`/channels/${id}/publications`"
          >К публикациям</RouterLink
        ></Button
      >
    </div>
    <Skeleton
      v-if="publication.isPending.value"
      class="h-96"
      aria-label="Загрузка карточки"
    />
    <Alert v-else-if="publication.isError.value" variant="destructive"
      ><AlertTitle>Не удалось загрузить карточку</AlertTitle
      ><AlertDescription
        >Проверьте, что публикация существует в текущем подключении.<Button
          variant="outline"
          @click="publication.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <template v-else-if="item">
      <Alert v-if="incomplete || item.warnings.length"
        ><AlertTitle>Не все данные карточки доступны</AlertTitle
        ><AlertDescription
          ><span v-if="incomplete"
            >Вариации получены частично: {{ item.variants.length }} из
            {{ item.expected_variations }}. </span
          >Отсутствующие поля отмечены как «Нет данных».</AlertDescription
        ></Alert
      >
      <div
        class="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
      >
        <Card
          ><CardHeader
            ><CardTitle>Изображения</CardTitle
            ><CardDescription
              >{{ item.images.length }} изображений из
              источника</CardDescription
            ></CardHeader
          ><CardContent
            ><div v-if="item.images.length" class="grid grid-cols-2 gap-3">
              <img
                v-for="image in item.images"
                :key="image.url"
                :src="image.url"
                :alt="image.alt || item.title || 'Товар'"
                class="aspect-square w-full rounded-md object-contain"
                loading="lazy"
                referrerpolicy="no-referrer"
              />
            </div>
            <p v-else class="text-sm text-muted-foreground">
              Нет данных
            </p></CardContent
          ></Card
        >
        <Card
          ><CardHeader
            ><CardTitle>{{ item.title ?? "Без названия" }}</CardTitle
            ><CardDescription
              >Получена {{ dateLabel(item.observed_at) }} · Ревизия
              {{ item.revision }}</CardDescription
            ></CardHeader
          ><CardContent class="flex flex-col gap-4">
            <dl class="grid gap-4 sm:grid-cols-2">
              <div>
                <dt class="text-sm text-muted-foreground">SKU</dt>
                <dd>{{ item.sku ?? "Нет данных" }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Внешний ID</dt>
                <dd>{{ item.external_id }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Цена</dt>
                <dd>{{ priceLabel(item.price, item.currency) }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Обычная цена</dt>
                <dd>{{ priceLabel(item.regular_price, item.currency) }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Цена со скидкой</dt>
                <dd>{{ priceLabel(item.sale_price, item.currency) }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Остаток</dt>
                <dd>{{ item.quantity ?? "Нет данных" }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Наличие</dt>
                <dd>{{ sourceLabel(item.availability) }}</dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">
                  Статус на платформе
                </dt>
                <dd>
                  <Badge variant="outline">{{
                    sourceLabel(item.source_status)
                  }}</Badge>
                </dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">Тип товара</dt>
                <dd>
                  {{
                    item.product_type
                      ? (typeLabels[item.product_type] ?? item.product_type)
                      : "Нет данных"
                  }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-muted-foreground">
                  Категории / группы
                </dt>
                <dd>
                  {{
                    item.categories.length
                      ? item.categories
                          .map(
                            (category) => category.name || category.external_id,
                          )
                          .join(", ")
                      : "Нет данных"
                  }}
                </dd>
              </div>
            </dl>
            <Button
              v-if="item.external_url"
              as-child
              variant="outline"
              class="w-fit"
              ><a
                :href="item.external_url"
                target="_blank"
                rel="noopener noreferrer"
                >Открыть на платформе</a
              ></Button
            >
          </CardContent></Card
        >
      </div>
      <Card
        ><CardHeader
          ><CardTitle>Описание</CardTitle
          ><CardDescription
            >Содержимое карточки из источника</CardDescription
          ></CardHeader
        ><CardContent class="flex flex-col gap-5">
          <section>
            <h3 class="mb-2 font-medium">Краткое описание</h3>
            <div
              v-if="item.short_description_html"
              class="publication-description"
              v-html="item.short_description_html"
            />
            <p v-else class="text-sm text-muted-foreground">Нет данных</p>
          </section>
          <section>
            <h3 class="mb-2 font-medium">Полное описание</h3>
            <div
              v-if="item.description_html"
              class="publication-description"
              v-html="item.description_html"
            />
            <p v-else class="text-sm text-muted-foreground">Нет данных</p>
          </section>
        </CardContent></Card
      >
      <Card
        ><CardHeader
          ><CardTitle>Характеристики</CardTitle
          ><CardDescription
            >Названия и значения на внешней платформе</CardDescription
          ></CardHeader
        ><CardContent
          ><Table v-if="item.attributes.length"
            ><TableHeader
              ><TableRow
                ><TableHead>Характеристика</TableHead
                ><TableHead>Значение</TableHead></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow
                v-for="(attribute, index) in item.attributes"
                :key="index"
                ><TableCell>{{ attribute.name }}</TableCell
                ><TableCell
                  >{{ attribute.value }} {{ attribute.unit }}</TableCell
                ></TableRow
              ></TableBody
            ></Table
          >
          <p v-else class="text-sm text-muted-foreground">
            Нет данных
          </p></CardContent
        ></Card
      >
      <Card v-if="item.expected_variations || item.variants.length"
        ><CardHeader
          ><CardTitle>Вариации</CardTitle
          ><CardDescription
            >{{ item.variants.length }} полученных позиций</CardDescription
          ></CardHeader
        ><CardContent
          ><Table
            ><TableHeader
              ><TableRow
                ><TableHead>Вариация / SKU</TableHead
                ><TableHead>Характеристики</TableHead><TableHead>Цена</TableHead
                ><TableHead>Остаток</TableHead><TableHead>Наличие</TableHead
                ><TableHead>Статус</TableHead></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-for="variant in item.variants" :key="variant.id"
                ><TableCell
                  ><RouterLink
                    :to="`/channels/${id}/publications/${variant.id}`"
                    class="font-medium hover:underline"
                    >{{
                      variant.title ?? `Вариант #${variant.external_id}`
                    }}</RouterLink
                  >
                  <div class="text-sm text-muted-foreground">
                    {{ variant.sku ?? "Нет SKU" }} · {{ variant.external_id }}
                  </div></TableCell
                ><TableCell>{{
                  variant.attributes
                    .map((attribute) => `${attribute.name}: ${attribute.value}`)
                    .join(", ") || "Нет данных"
                }}</TableCell
                ><TableCell>{{
                  priceLabel(variant.price, variant.currency)
                }}</TableCell
                ><TableCell>{{ variant.quantity ?? "Нет данных" }}</TableCell
                ><TableCell>{{ sourceLabel(variant.availability) }}</TableCell
                ><TableCell>{{
                  sourceLabel(variant.source_status)
                }}</TableCell></TableRow
              ></TableBody
            ></Table
          ></CardContent
        ></Card
      >
    </template>
  </div>
</template>
<style scoped>
.publication-description {
  overflow-wrap: anywhere;
}
.publication-description :deep(p) {
  margin-bottom: 0.75rem;
}
.publication-description :deep(ul),
.publication-description :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}
.publication-description :deep(ul) {
  list-style: disc;
}
.publication-description :deep(ol) {
  list-style: decimal;
}
.publication-description :deep(a) {
  text-decoration: underline;
}
.publication-description :deep(table) {
  display: block;
  overflow-x: auto;
}
</style>
