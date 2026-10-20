<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
defineProps<{ title: string; pending: boolean; error: string | null }>();
defineEmits<{ close: []; confirm: [] }>();
</script>
<template>
  <Dialog
    :open="true"
    @update:open="
      (value) => {
        if (!value && !pending) $emit('close');
      }
    "
    ><DialogContent
      :show-close-button="!pending"
      @escape-key-down="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      @interact-outside="
        (event) => {
          if (pending) event.preventDefault();
        }
      "
      ><DialogHeader
        ><DialogTitle>Снять связь с товаром?</DialogTitle
        ><DialogDescription
          >{{ title }} · Товар каталога и внешняя публикация сохранятся. История
          привязки останется в системе.</DialogDescription
        ></DialogHeader
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="pending" @click="$emit('close')"
          >Отмена</Button
        ><Button :disabled="pending" @click="$emit('confirm')">{{
          pending ? "Снимаем связь…" : "Снять связь"
        }}</Button>
      </div></DialogContent
    ></Dialog
  >
</template>
