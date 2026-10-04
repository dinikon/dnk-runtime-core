<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiErrorMessage } from "@/app/providers/http";
import {
  crmCompaniesApi,
  crmContactsApi,
  crmContactPointsApi,
  crmRelationsApi,
} from "../../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "../../model/crm.query-keys";
import type { CrmKind, CrmRecord } from "../../model/crm.types";
import CrmRecordLink from "./CrmRecordLink.vue";

const props = withDefaults(
  defineProps<{ kind: CrmKind; id: string; showExtensions?: boolean }>(),
  {
    showExtensions: true,
  },
);
const detail = useQuery({
  queryKey: computed(() => crmKeys.detail(props.kind, props.id)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmContactsApi.get(props.id, signal)
      : await crmCompaniesApi.get(props.id, signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const relations = useQuery({
  queryKey: computed(() => crmKeys.relations(props.kind, props.id)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmRelationsApi.companies(props.id, signal)
      : await crmRelationsApi.contacts(props.id, signal),
  enabled: computed(() => props.showExtensions && detail.isSuccess.value),
  staleTime: CRM_QUERY_STALE_TIME,
});
const points = useQuery({
  queryKey: computed(() => crmKeys.points(props.kind, props.id)),
  queryFn: ({ signal }) =>
    crmContactPointsApi.get(props.kind, props.id, signal),
  enabled: computed(() => props.showExtensions && detail.isSuccess.value),
  staleTime: CRM_QUERY_STALE_TIME,
});
const relatedKind = computed(() =>
  props.kind === "contacts" ? "companies" : "contacts",
);
function name(item: CrmRecord) {
  return "displayName" in item ? item.displayName : item.legalName;
}
function date(value: string) {
  return new Date(value).toLocaleString("uk-UA");
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-5">
    <div
      v-if="detail.isPending.value"
      class="flex flex-col gap-3"
      role="status"
    >
      <Skeleton class="h-8 w-2/3" />
      <Skeleton class="h-28" />
    </div>
    <Alert v-else-if="detail.isError.value" variant="destructive">
      <AlertDescription class="flex items-center gap-3">
        {{
          getApiErrorMessage(detail.error.value, "Не удалось загрузить запись.")
        }}
        <Button variant="outline" size="sm" @click="detail.refetch()"
          >Повторить</Button
        >
      </AlertDescription>
    </Alert>
    <template v-else-if="detail.data.value">
      <Card>
        <CardHeader
          ><CardTitle class="break-words">{{
            name(detail.data.value)
          }}</CardTitle></CardHeader
        >
        <CardContent class="flex flex-col gap-2 text-sm">
          <template v-if="'firstName' in detail.data.value">
            <p>
              <span class="text-muted-foreground">Имя:</span>
              {{ detail.data.value.firstName }}
            </p>
            <p v-if="detail.data.value.lastName">
              <span class="text-muted-foreground">Фамилия:</span>
              {{ detail.data.value.lastName }}
            </p>
            <p v-if="detail.data.value.middleName">
              <span class="text-muted-foreground">Отчество:</span>
              {{ detail.data.value.middleName }}
            </p>
          </template>
          <p class="text-muted-foreground">
            Создано: {{ date(detail.data.value.createdAt) }}
          </p>
          <p class="text-muted-foreground">
            Обновлено: {{ date(detail.data.value.updatedAt) }}
          </p>
        </CardContent>
      </Card>
      <Card v-if="showExtensions">
        <CardHeader
          ><CardTitle>{{
            kind === "contacts" ? "Компании" : "Контакты"
          }}</CardTitle></CardHeader
        >
        <CardContent>
          <Skeleton v-if="relations.isPending.value" class="h-10" />
          <Alert v-else-if="relations.isError.value" variant="destructive">
            <AlertDescription
              >Не удалось загрузить связи.
              <Button variant="outline" size="sm" @click="relations.refetch()"
                >Повторить</Button
              ></AlertDescription
            >
          </Alert>
          <ul
            v-else-if="relations.data.value?.length"
            class="flex flex-col gap-2"
          >
            <li v-for="item in relations.data.value" :key="item.id">
              <CrmRecordLink
                :kind="relatedKind"
                :id="item.id"
                class="text-primary hover:underline"
              >
                {{ name(item) }}
              </CrmRecordLink>
            </li>
          </ul>
          <p v-else class="text-sm text-muted-foreground">Связей пока нет.</p>
        </CardContent>
      </Card>
      <Card v-if="showExtensions">
        <CardHeader><CardTitle>Контактные данные</CardTitle></CardHeader>
        <CardContent class="flex flex-col gap-4 text-sm">
          <Skeleton v-if="points.isPending.value" class="h-16" />
          <Alert v-else-if="points.isError.value" variant="destructive">
            <AlertDescription
              >Не удалось загрузить контактные данные.
              <Button variant="outline" size="sm" @click="points.refetch()"
                >Повторить</Button
              ></AlertDescription
            >
          </Alert>
          <template v-else>
            <div>
              <p class="font-medium">Телефоны</p>
              <ul
                v-if="points.data.value?.phones.length"
                class="flex flex-col gap-1"
              >
                <li
                  v-for="row in points.data.value.phones"
                  :key="row.clientKey"
                >
                  <a
                    class="text-primary hover:underline"
                    :href="`tel:${row.value}`"
                    >{{ row.value }}</a
                  >
                </li>
              </ul>
              <p v-else class="text-muted-foreground">Не указаны.</p>
            </div>
            <div>
              <p class="font-medium">Email</p>
              <ul
                v-if="points.data.value?.emails.length"
                class="flex flex-col gap-1"
              >
                <li
                  v-for="row in points.data.value.emails"
                  :key="row.clientKey"
                >
                  <a
                    class="text-primary hover:underline"
                    :href="`mailto:${row.value}`"
                    >{{ row.value }}</a
                  >
                </li>
              </ul>
              <p v-else class="text-muted-foreground">Не указаны.</p>
            </div>
          </template>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
