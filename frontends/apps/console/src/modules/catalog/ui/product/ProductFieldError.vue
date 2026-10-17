<script setup lang="ts">
import { FieldError } from "@/components/ui/field";
defineProps<{ id: string; error?: string }>();
</script>
<template>
  <FieldError v-if="error" :id="id" role="alert">{{ error }}</FieldError>
</template>
