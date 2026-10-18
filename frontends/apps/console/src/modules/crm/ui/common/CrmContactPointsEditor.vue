<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  ContactPointsWidget,
  contactPointServerErrors,
  useContactPointLabels,
  validateContactPoints,
} from "@/modules/contact-points";
import type {
  ContactPointDraft,
  ContactPointErrors,
} from "@/modules/contact-points";
import { crmContactPointsApi } from "../../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "../../model/crm.query-keys";
import type { CrmKind } from "../../model/crm.types";

const props = defineProps<{ kind: CrmKind; id: string }>();
const queryClient = useQueryClient();
const points = useQuery({
  queryKey: computed(() => crmKeys.points(props.kind, props.id)),
  queryFn: ({ signal }) =>
    crmContactPointsApi.get(props.kind, props.id, signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const editing = ref(false);
const phones = ref<ContactPointDraft[]>([]);
const emails = ref<ContactPointDraft[]>([]);
const errors = ref<ContactPointErrors>({});
const attempted = ref(false);
const valid = ref(true);
const labels = useContactPointLabels(editing);
watch(
  () => props.id,
  () => {
    editing.value = false;
  },
);
watch([phones, emails], (current, previous) => {
  const rows = new Map(current.flat().map((row) => [row.clientKey, row]));
  for (const old of previous.flat()) {
    const row = rows.get(old.clientKey);
    if (
      !row ||
      row.value !== old.value ||
      row.countryCode !== old.countryCode ||
      row.labelId !== old.labelId
    )
      delete errors.value[old.clientKey];
  }
});
function begin() {
  if (!points.data.value) return;
  phones.value = points.data.value.phones.map((item) => ({ ...item }));
  emails.value = points.data.value.emails.map((item) => ({ ...item }));
  errors.value = {};
  attempted.value = false;
  editing.value = true;
}
const mutation = useMutation({
  mutationFn: () =>
    crmContactPointsApi.replace(props.kind, props.id, {
      phones: phones.value,
      emails: emails.value,
    }),
  onSuccess: (result) => {
    queryClient.setQueryData(crmKeys.points(props.kind, props.id), result);
    editing.value = false;
    toast.success("Контактные данные сохранены");
  },
  onError: (cause) => {
    errors.value = contactPointServerErrors(cause, {
      phones: phones.value,
      emails: emails.value,
    });
    toast.error(
      getApiErrorMessage(cause, "Не удалось сохранить контактные данные."),
    );
  },
});
function save() {
  attempted.value = true;
  if (
    !valid.value ||
    mutation.isPending.value ||
    Object.keys(validateContactPoints(phones.value, "phone")).length ||
    Object.keys(validateContactPoints(emails.value, "email")).length
  )
    return;
  mutation.mutate();
}
</script>

<template>
  <Card>
    <CardHeader><CardTitle>Контактные данные</CardTitle></CardHeader>
    <CardContent class="flex flex-col gap-4">
      <Skeleton v-if="points.isPending.value" class="h-20" />
      <Alert v-else-if="points.isError.value" variant="destructive">
        <AlertDescription
          >Не удалось загрузить контактные данные.
          <Button variant="outline" size="sm" @click="points.refetch()"
            >Повторить</Button
          ></AlertDescription
        >
      </Alert>
      <template v-else-if="!editing">
        <div class="flex flex-col gap-1 text-sm">
          <p class="font-medium">Телефоны</p>
          <a
            v-for="row in points.data.value?.phones ?? []"
            :key="row.clientKey"
            class="text-primary hover:underline"
            :href="`tel:${row.value}`"
            >{{ row.value }}</a
          >
          <p
            v-if="!points.data.value?.phones.length"
            class="text-muted-foreground"
          >
            Не указаны.
          </p>
        </div>
        <div class="flex flex-col gap-1 text-sm">
          <p class="font-medium">Email</p>
          <a
            v-for="row in points.data.value?.emails ?? []"
            :key="row.clientKey"
            class="text-primary hover:underline"
            :href="`mailto:${row.value}`"
            >{{ row.value }}</a
          >
          <p
            v-if="!points.data.value?.emails.length"
            class="text-muted-foreground"
          >
            Не указаны.
          </p>
        </div>
        <Button variant="outline" class="self-start" @click="begin"
          >Редактировать</Button
        >
      </template>
      <template v-else>
        <ContactPointsWidget
          v-model:phones="phones"
          v-model:emails="emails"
          :labels="labels.data.value ?? []"
          :pending="mutation.isPending.value"
          :attempted="attempted"
          :errors="errors"
          :labels-loading="labels.isFetching.value"
          :labels-error="labels.isError.value"
          @validation-change="valid = $event"
          @retry="labels.refetch()"
        />
        <Alert v-if="mutation.isError.value" variant="destructive"
          ><AlertDescription>{{
            getApiErrorMessage(
              mutation.error.value,
              "Не удалось сохранить контактные данные.",
            )
          }}</AlertDescription></Alert
        >
        <div class="flex gap-2">
          <Button :disabled="mutation.isPending.value" @click="save"
            ><Spinner
              v-if="mutation.isPending.value"
              data-icon="inline-start"
            />Сохранить</Button
          >
          <Button
            variant="outline"
            :disabled="mutation.isPending.value"
            @click="editing = false"
            >Отмена</Button
          >
        </div>
      </template>
    </CardContent>
  </Card>
</template>
