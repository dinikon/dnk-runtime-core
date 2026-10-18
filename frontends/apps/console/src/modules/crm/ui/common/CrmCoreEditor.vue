<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { crmCompaniesApi, crmContactsApi } from "../../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "../../model/crm.query-keys";
import type { CrmKind } from "../../model/crm.types";

const props = defineProps<{ kind: CrmKind; id: string }>();
const queryClient = useQueryClient();
const detail = useQuery({
  queryKey: computed(() => crmKeys.detail(props.kind, props.id)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmContactsApi.get(props.id, signal)
      : await crmCompaniesApi.get(props.id, signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const editing = ref(false);
const attempted = ref(false);
const firstName = ref("");
const lastName = ref("");
const middleName = ref("");
const legalName = ref("");
watch(
  () => props.id,
  () => {
    editing.value = false;
  },
);
function begin() {
  const item = detail.data.value;
  if (!item) return;
  if ("firstName" in item) {
    firstName.value = item.firstName;
    lastName.value = item.lastName ?? "";
    middleName.value = item.middleName ?? "";
  } else legalName.value = item.legalName;
  attempted.value = false;
  editing.value = true;
}
const mutation = useMutation({
  mutationFn: async () =>
    props.kind === "contacts"
      ? await crmContactsApi.update(props.id, {
          firstName: firstName.value.trim(),
          lastName: lastName.value.trim() || null,
          middleName: middleName.value.trim() || null,
        })
      : await crmCompaniesApi.update(props.id, {
          legalName: legalName.value.trim(),
        }),
  onSuccess: async () => {
    editing.value = false;
    toast.success("Запись обновлена");
    await queryClient.invalidateQueries({ queryKey: crmKeys.all });
  },
  onError: (cause) =>
    toast.error(getApiErrorMessage(cause, "Не удалось сохранить запись.")),
});
function save() {
  attempted.value = true;
  const value =
    props.kind === "contacts" ? firstName.value.trim() : legalName.value.trim();
  if (!value || value.length > 255 || mutation.isPending.value) return;
  mutation.mutate();
}
</script>

<template>
  <Card>
    <CardHeader><CardTitle>Основные данные</CardTitle></CardHeader>
    <CardContent class="flex flex-col gap-4">
      <Button
        v-if="!editing"
        variant="outline"
        class="self-start"
        :disabled="!detail.data.value"
        @click="begin"
        >Редактировать</Button
      >
      <form v-else class="flex flex-col gap-4" @submit.prevent="save">
        <FieldGroup>
          <template v-if="kind === 'contacts'">
            <Field
              :data-invalid="attempted && !firstName.trim() ? true : undefined"
            >
              <FieldLabel for="record-first-name">Имя</FieldLabel>
              <Input
                id="record-first-name"
                v-model="firstName"
                maxlength="255"
                required
                :disabled="mutation.isPending.value"
                :aria-invalid="attempted && !firstName.trim()"
              />
              <FieldError v-if="attempted && !firstName.trim()"
                >Укажите имя.</FieldError
              >
            </Field>
            <Field
              ><FieldLabel for="record-last-name">Фамилия</FieldLabel
              ><Input
                id="record-last-name"
                v-model="lastName"
                maxlength="255"
                :disabled="mutation.isPending.value"
            /></Field>
            <Field
              ><FieldLabel for="record-middle-name">Отчество</FieldLabel
              ><Input
                id="record-middle-name"
                v-model="middleName"
                maxlength="255"
                :disabled="mutation.isPending.value"
            /></Field>
          </template>
          <Field
            v-else
            :data-invalid="attempted && !legalName.trim() ? true : undefined"
          >
            <FieldLabel for="record-legal-name">Название</FieldLabel>
            <Input
              id="record-legal-name"
              v-model="legalName"
              maxlength="255"
              required
              :disabled="mutation.isPending.value"
              :aria-invalid="attempted && !legalName.trim()"
            />
            <FieldError v-if="attempted && !legalName.trim()"
              >Укажите название.</FieldError
            >
          </Field>
        </FieldGroup>
        <Alert v-if="mutation.isError.value" variant="destructive"
          ><AlertDescription>{{
            getApiErrorMessage(
              mutation.error.value,
              "Не удалось сохранить запись.",
            )
          }}</AlertDescription></Alert
        >
        <div class="flex gap-2">
          <Button type="submit" :disabled="mutation.isPending.value"
            ><Spinner
              v-if="mutation.isPending.value"
              data-icon="inline-start"
            />Сохранить</Button
          >
          <Button
            type="button"
            variant="outline"
            :disabled="mutation.isPending.value"
            @click="editing = false"
            >Отмена</Button
          >
        </div>
      </form>
    </CardContent>
  </Card>
</template>
