<script setup lang="ts">
import { useSeoMeta, useRequestEvent } from "#imports";
import { setResponseStatus } from "h3";
import NotFoundPage from "../modules/home/NotFoundPage.vue";

useSeoMeta({ title: "Страница не найдена · dNiko Alpha", robots: "noindex, nofollow" });
if (import.meta.server) {
  const event = useRequestEvent();
  if (event) setResponseStatus(event, 404);
}
</script>

<template><NotFoundPage /></template>
