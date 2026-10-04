<script setup lang="ts">
import { computed } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { Plus, X } from "@lucide/vue";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import {
  crmCompaniesApi,
  crmContactsApi,
  crmRelationsApi,
} from "../../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "../../model/crm.query-keys";
import type { CrmKind, CrmRecord } from "../../model/crm.types";
import CrmRecordLink from "./CrmRecordLink.vue";

const props = defineProps<{ kind: CrmKind; id: string }>();
const queryClient = useQueryClient();
const relatedKind = computed(() =>
  props.kind === "contacts" ? "companies" : "contacts",
);
const related = useQuery({
  queryKey: computed(() => crmKeys.relations(props.kind, props.id)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmRelationsApi.companies(props.id, signal)
      : await crmRelationsApi.contacts(props.id, signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const candidates = useQuery({
  queryKey: computed(() => crmKeys.list(relatedKind.value)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmCompaniesApi.list(signal)
      : await crmContactsApi.list(signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const available = computed(() => {
  const ids = new Set(related.data.value?.map((item) => item.id) ?? []);
  return candidates.data.value?.filter((item) => !ids.has(item.id)) ?? [];
});
function name(item: CrmRecord) {
  return "displayName" in item ? item.displayName : item.legalName;
}
const link = useMutation({
  mutationFn: (id: string) => crmRelationsApi.link(props.kind, props.id, id),
  onSuccess: async (_, relatedId) => {
    toast.success("Связь добавлена");
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: crmKeys.relations(props.kind, props.id),
      }),
      queryClient.invalidateQueries({
        queryKey: crmKeys.relations(relatedKind.value, relatedId),
      }),
    ]);
  },
  onError: (cause) =>
    toast.error(getApiErrorMessage(cause, "Не удалось добавить связь.")),
});
const unlink = useMutation({
  mutationFn: (id: string) => crmRelationsApi.unlink(props.kind, props.id, id),
  onSuccess: async (_, relatedId) => {
    toast.success("Связь удалена");
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: crmKeys.relations(props.kind, props.id),
      }),
      queryClient.invalidateQueries({
        queryKey: crmKeys.relations(relatedKind.value, relatedId),
      }),
    ]);
  },
  onError: (cause) =>
    toast.error(getApiErrorMessage(cause, "Не удалось удалить связь.")),
});
</script>

<template>
  <Card>
    <CardHeader
      ><CardTitle>{{
        kind === "contacts" ? "Компании" : "Контакты"
      }}</CardTitle></CardHeader
    >
    <CardContent class="flex flex-col gap-4">
      <Skeleton v-if="related.isPending.value" class="h-10" />
      <Alert v-else-if="related.isError.value" variant="destructive">
        <AlertDescription
          >Не удалось загрузить связи.
          <Button variant="outline" size="sm" @click="related.refetch()"
            >Повторить</Button
          ></AlertDescription
        >
      </Alert>
      <ul v-else-if="related.data.value?.length" class="flex flex-col gap-2">
        <li
          v-for="item in related.data.value"
          :key="item.id"
          class="flex items-center justify-between gap-2"
        >
          <CrmRecordLink
            :kind="relatedKind"
            :id="item.id"
            class="min-w-0 break-words text-primary hover:underline"
            >{{ name(item) }}</CrmRecordLink
          >
          <Button
            variant="ghost"
            size="icon"
            :aria-label="`Отвязать: ${name(item)}`"
            :disabled="unlink.isPending.value || link.isPending.value"
            @click="unlink.mutate(item.id)"
            ><X
          /></Button>
        </li>
      </ul>
      <p v-else class="text-sm text-muted-foreground">Связей пока нет.</p>
      <Popover>
        <PopoverTrigger as-child
          ><Button
            variant="outline"
            class="self-start"
            :disabled="link.isPending.value || unlink.isPending.value"
            ><Plus data-icon="inline-start" />Добавить связь</Button
          ></PopoverTrigger
        >
        <PopoverContent class="flex max-h-72 flex-col gap-2 overflow-y-auto">
          <Alert v-if="candidates.isError.value" variant="destructive"
            ><AlertDescription
              >Не удалось загрузить список.
              <Button variant="outline" size="sm" @click="candidates.refetch()"
                >Повторить</Button
              ></AlertDescription
            ></Alert
          >
          <Skeleton v-else-if="candidates.isPending.value" class="h-10" />
          <p
            v-else-if="!available.length"
            class="text-sm text-muted-foreground"
          >
            Нет доступных записей.
          </p>
          <Button
            v-for="item in available"
            :key="item.id"
            variant="ghost"
            class="justify-start whitespace-normal text-left"
            :disabled="link.isPending.value"
            @click="link.mutate(item.id)"
            >{{ name(item) }}</Button
          >
        </PopoverContent>
      </Popover>
    </CardContent>
  </Card>
</template>
