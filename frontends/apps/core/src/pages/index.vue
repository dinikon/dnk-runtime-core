<script setup lang="ts">
import { useHead, useRuntimeConfig, useSeoMeta } from "#imports";
import HomePage from "../modules/home/HomePage.vue";

const config = useRuntimeConfig();
const canonical = new URL("/", config.public.siteUrl).href;
const title = "dNiko Alpha — единый аккаунт для вашей работы";
const description = "Управляйте профилем, способами входа и безопасностью в одном месте";
useSeoMeta({ title, description, ogTitle: title, ogDescription: description, ogUrl: canonical, ogType: "website", ogSiteName: "dNiko Alpha", twitterCard: "summary" });
useHead({ link: [{ rel: "canonical", href: canonical }] });
</script>

<template><HomePage /></template>
