<script setup lang="ts">
import { ref } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Platform, CreateChannelInput } from "../model/channels.types";
const props = defineProps<{
  open: boolean;
  platforms: Platform[];
  pending: boolean;
  error: string | null;
}>();
const emit = defineEmits<{ close: []; submit: [input: CreateChannelInput] }>();
const name = ref(""),
  platformKind = ref("");
function submit(): void {
  if (name.value.trim() && platformKind.value && !props.pending)
    emit("submit", {
      name: name.value.trim(),
      platformKind: platformKind.value,
    });
}
</script>
<template>
  <Dialog
    :open="open"
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
        ><DialogTitle>Добавить канал</DialogTitle
        ><DialogDescription
          >Один канал — один магазин или источник продаж.</DialogDescription
        ></DialogHeader
      >
      <form class="flex flex-col gap-5" @submit.prevent="submit">
        <FieldGroup
          ><Field
            ><FieldLabel for="channel-name">Название</FieldLabel
            ><Input
              id="channel-name"
              v-model="name"
              required
              maxlength="200"
              :disabled="pending"
              placeholder="Например, основной магазин" /></Field
          ><Field
            ><FieldLabel for="channel-platform">Платформа</FieldLabel
            ><NativeSelect
              id="channel-platform"
              v-model="platformKind"
              required
              :disabled="pending"
              ><NativeSelectOption value="" disabled
                >Выберите платформу</NativeSelectOption
              ><NativeSelectOption
                v-for="platform in platforms"
                :key="platform.kind"
                :value="platform.kind"
                >{{ platform.label }}</NativeSelectOption
              ></NativeSelect
            ></Field
          ></FieldGroup
        ><Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <div class="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="$emit('close')"
            >Отмена</Button
          ><Button
            type="submit"
            :disabled="pending || !name.trim() || !platformKind"
            >{{ pending ? "Создаём…" : "Создать канал" }}</Button
          >
        </div>
      </form></DialogContent
    ></Dialog
  >
</template>
