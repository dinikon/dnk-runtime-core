<script setup lang="ts">
import { RouterView } from "vue-router";
import { provideCrmNavigation } from "../model/use-crm-navigation";
import CrmPreviewStack from "../ui/common/CrmPreviewStack.vue";

provideCrmNavigation();
</script>

<template>
  <RouterView />
  <CrmPreviewStack />
</template>
