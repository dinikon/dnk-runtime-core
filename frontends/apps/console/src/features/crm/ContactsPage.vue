<script setup lang="ts">
import ContactsTable from "./ContactsTable.vue";
import { AppLayout } from "@/layouts";
</script>

<template>
  <AppLayout>
    <template #header>
      <h1 class="truncate text-base font-semibold text-neutral-800">
        Contacts
      </h1>
    </template>

    <ContactsTable />
  </AppLayout>
</template>
