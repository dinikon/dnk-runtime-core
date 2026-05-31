<script setup lang="ts">
import { RuntimeObjectPage } from "@/shared/runtime-object";
import { contactsRuntimeObject } from "@/modules/crm/models/contacts-runtime-object";
</script>

<template>
  <RuntimeObjectPage :resource="contactsRuntimeObject" />
</template>
