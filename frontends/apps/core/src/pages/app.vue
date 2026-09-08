<script setup lang="ts">
import { definePageMeta, useSeoMeta } from "#imports";
import WorkspacePage from "../modules/workspace/WorkspacePage.vue";

definePageMeta({ middleware: "auth", requiresAuth: true });
useSeoMeta({ title: "Мой аккаунт · dNiko Alpha", robots: "noindex, nofollow" });
</script>

<template><WorkspacePage /></template>
