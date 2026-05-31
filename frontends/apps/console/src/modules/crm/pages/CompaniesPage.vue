<script setup lang="ts">
import { RuntimeObjectPage } from "@/shared/runtime-object";
import { companiesRuntimeObject } from "@/modules/crm/models/companies-runtime-object";
</script>

<template>
  <RuntimeObjectPage :resource="companiesRuntimeObject" />
</template>
