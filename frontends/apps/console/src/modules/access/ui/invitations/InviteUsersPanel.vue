<script setup lang="ts">
import { Plus, Trash2, UserPlus } from "@lucide/vue";
import { watch, ref } from "vue";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { InvitationInput, Role } from "../../model/access.types";

const props = defineProps<{
  pending: boolean;
  resetKey: number;
}>();
const emit = defineEmits<{
  submit: [items: InvitationInput[]];
}>();

interface InviteRow {
  id: string;
  email: string;
  role: Role;
  error: string;
}

const emailSchema = z.string().trim().email("Введите корректный email.");
const rows = ref<InviteRow[]>([createRow()]);

function createRow(): InviteRow {
  return {
    id: crypto.randomUUID(),
    email: "",
    role: "member",
    error: "",
  };
}

function reset() {
  rows.value = [createRow()];
}

watch(() => props.resetKey, reset);

function addRow() {
  rows.value.push(createRow());
}

function removeRow(id: string) {
  if (rows.value.length === 1) return;
  rows.value = rows.value.filter((row) => row.id !== id);
}

function submit() {
  const seen = new Set<string>();
  let valid = true;

  for (const row of rows.value) {
    row.error = "";
    const result = emailSchema.safeParse(row.email);
    if (!result.success) {
      row.error = result.error.issues[0]?.message ?? "Проверьте email.";
      valid = false;
      continue;
    }

    const normalized = result.data.toLowerCase();
    if (seen.has(normalized)) {
      row.error = "Этот email уже добавлен в форму.";
      valid = false;
      continue;
    }
    seen.add(normalized);
    row.email = normalized;
  }

  if (!valid) return;
  emit(
    "submit",
    rows.value.map(({ email, role }) => ({ email, role })),
  );
}
</script>

<template>
  <Card class="overflow-hidden">
    <CardHeader
      class="flex flex-row items-center justify-between gap-4 border-b"
    >
      <CardTitle class="text-base">Пригласить пользователей по email</CardTitle>
      <Button type="submit" form="invite-users-form" :disabled="pending">
        <UserPlus />
        {{ pending ? "Отправляем…" : "Пригласить" }}
      </Button>
    </CardHeader>
    <CardContent class="pt-6">
      <form id="invite-users-form" class="grid gap-4" @submit.prevent="submit">
        <div
          v-for="(row, index) in rows"
          :key="row.id"
          class="grid items-start gap-3 md:grid-cols-[minmax(0,1fr)_14rem_auto]"
        >
          <Field>
            <FieldLabel :for="`invite-email-${row.id}`">
              Email<span v-if="rows.length > 1"> {{ index + 1 }}</span>
            </FieldLabel>
            <Input
              :id="`invite-email-${row.id}`"
              v-model="row.email"
              type="email"
              autocomplete="email"
              placeholder="name@company.com"
              :aria-invalid="Boolean(row.error)"
              :disabled="pending"
              @input="row.error = ''"
            />
            <FieldError v-if="row.error">{{ row.error }}</FieldError>
          </Field>
          <Field>
            <FieldLabel :for="`invite-role-${row.id}`">Роль</FieldLabel>
            <Select v-model="row.role" :disabled="pending">
              <SelectTrigger :id="`invite-role-${row.id}`">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="member">Участник</SelectItem>
                  <SelectItem value="admin">Администратор</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
          <Button
            v-if="rows.length > 1"
            type="button"
            variant="ghost"
            size="icon"
            class="mt-6"
            :disabled="pending"
            :aria-label="`Удалить email ${index + 1}`"
            @click="removeRow(row.id)"
          >
            <Trash2 />
          </Button>
        </div>
        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="pending"
            @click="addRow"
          >
            <Plus />
            Добавить ещё
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>
