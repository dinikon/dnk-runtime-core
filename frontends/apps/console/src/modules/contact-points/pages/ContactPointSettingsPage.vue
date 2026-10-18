<script setup lang="ts">
import { computed, ref } from "vue";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";
import {
  useContactPointLabels,
  contactPointKeys,
} from "../model/use-labels-query";
import { contactPointsApi } from "../api/contact-points.api";
import type { ContactPointKind, ContactPointLabel } from "../model/types";
import LabelRow from "../ui/LabelRow.vue";
const labels = useContactPointLabels();
const queryClient = useQueryClient();
const newNames = ref({ phone: "", email: "" });
const attempted = ref({ phone: false, email: false });
const kinds: ContactPointKind[] = ["phone", "email"];
const refresh = () =>
  queryClient.invalidateQueries({ queryKey: contactPointKeys.labels });
const create = useMutation({
  mutationFn: ({ type, name }: { type: ContactPointKind; name: string }) =>
    contactPointsApi.createLabel(type, name),
  onSuccess: async (_, input) => {
    newNames.value[input.type] = "";
    attempted.value[input.type] = false;
    await refresh();
    toast.success("Подпись добавлена");
  },
});
const update = useMutation({
  mutationFn: ({
    id,
    changes,
  }: {
    id: string;
    changes: { name?: string; isActive?: boolean };
  }) => contactPointsApi.updateLabel(id, changes),
  onSuccess: async () => {
    await refresh();
    toast.success("Подпись обновлена");
  },
});
const pending = computed(
  () => create.isPending.value || update.isPending.value,
);
const error = ref("");
async function add(type: ContactPointKind) {
  attempted.value[type] = true;
  if (!newNames.value[type].trim() || pending.value) return;
  error.value = "";
  try {
    await create.mutateAsync({ type, name: newNames.value[type].trim() });
  } catch (cause) {
    error.value = getApiErrorMessage(cause, "Не удалось добавить подпись.");
  }
}
async function change(
  id: string,
  changes: { name?: string; isActive?: boolean },
) {
  error.value = "";
  try {
    await update.mutateAsync({ id, changes });
  } catch (cause) {
    error.value = getApiErrorMessage(cause, "Не удалось изменить подпись.");
  }
}
function toggle(label: ContactPointLabel) {
  return change(label.id, { isActive: !label.isActive });
}
</script>
<template>
  <div class="flex min-w-0 flex-col gap-6 overflow-y-auto pb-6">
    <header class="flex flex-col gap-2">
      <h1 class="text-2xl font-semibold">Точки контакта</h1>
      <p class="text-sm text-muted-foreground">
        Подписи телефонов и email для всех карточек рабочего пространства.
      </p>
    </header>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <div
      v-if="labels.isPending.value"
      role="status"
      class="flex items-center gap-2"
    >
      <Spinner />Загрузка подписей…
    </div>
    <Alert v-else-if="labels.isError.value" variant="destructive"
      ><AlertDescription
        >Не удалось загрузить подписи.<Button
          type="button"
          variant="outline"
          @click="labels.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Tabs v-else default-value="phone" class="w-full max-w-3xl">
      <TabsList
        ><TabsTrigger value="phone">Телефоны</TabsTrigger
        ><TabsTrigger value="email">Email</TabsTrigger></TabsList
      >
      <TabsContent
        v-for="kind in kinds"
        :key="kind"
        :value="kind"
        class="flex flex-col gap-4 pt-4"
      >
        <p class="text-sm text-muted-foreground">
          Архивные подписи остаются у существующих связей и недоступны для
          новых.
        </p>
        <LabelRow
          v-for="label in (labels.data.value ?? []).filter(
            (row) => row.type === kind,
          )"
          :key="label.id"
          :label="label"
          :pending="pending"
          @save="(id, name) => change(id, { name })"
          @toggle="toggle"
        />
        <Separator />
        <form
          class="flex items-start gap-2"
          @submit.prevent="add(kind)"
          novalidate
        >
          <Field
            class="min-w-0 flex-1"
            :data-invalid="
              (attempted[kind] && !newNames[kind].trim()) || undefined
            "
          >
            <FieldLabel :for="`new-label-${kind}`" class="sr-only"
              >Новая подпись</FieldLabel
            >
            <Input
              :id="`new-label-${kind}`"
              v-model="newNames[kind]"
              maxlength="100"
              placeholder="Новая подпись"
              :disabled="pending"
              :aria-invalid="attempted[kind] && !newNames[kind].trim()"
            />
            <FieldError v-if="attempted[kind] && !newNames[kind].trim()"
              >Введите название подписи.</FieldError
            >
          </Field>
          <Button type="submit" :disabled="pending"
            ><Spinner
              v-if="create.isPending.value"
              data-icon="inline-start"
            />Добавить</Button
          >
        </form>
      </TabsContent>
    </Tabs>
  </div>
</template>
