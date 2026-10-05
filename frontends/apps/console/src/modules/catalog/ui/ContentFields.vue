<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldLabel, FieldDescription } from "@/components/ui/field";
defineProps<{ disabled?: boolean; invalid?: boolean }>();
const name = defineModel<string>("name", { required: true });
const description = defineModel<string>("description", { required: true });
</script>
<template>
  <Field :data-invalid="invalid"
    ><FieldLabel for="product-name">Название</FieldLabel
    ><Input
      id="product-name"
      v-model="name"
      :disabled="disabled"
      :aria-invalid="invalid"
    /><FieldDescription
      >От 1 до 255 символов после удаления пробелов по краям.</FieldDescription
    ></Field
  >
  <Field
    ><FieldLabel for="product-description">Описание</FieldLabel
    ><Textarea
      id="product-description"
      v-model="description"
      :disabled="disabled"
      rows="5"
  /></Field>
</template>
