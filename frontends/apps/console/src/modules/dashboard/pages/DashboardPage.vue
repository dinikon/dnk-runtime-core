<script setup lang="ts">
import { ContactRound, Settings, ShieldCheck } from "@lucide/vue";
import { RouterLink } from "vue-router";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const dashboardSections = [
  {
    title: "CRM",
    description: "Open contacts and customer records.",
    to: "/crm/contacts",
    icon: ContactRound,
  },
  {
    title: "Access",
    description: "Current session is active and protected by workspace auth.",
    icon: ShieldCheck,
  },
  {
    title: "Settings",
    description: "Workspace configuration will be available from here.",
    icon: Settings,
  },
];
</script>

<template>
  <div class="grid gap-4">
    <section class="grid gap-1">
      <h2 class="text-lg font-semibold tracking-normal">Home</h2>
      <p class="max-w-2xl text-sm text-muted-foreground">
        Start from the workspace overview, then move into operational modules.
      </p>
    </section>

    <section class="grid gap-3 md:grid-cols-3">
      <Card v-for="section in dashboardSections" :key="section.title">
        <CardHeader class="gap-2">
          <component
            :is="section.icon"
            class="size-4 text-muted-foreground"
            aria-hidden="true"
          />
          <CardTitle class="text-sm">{{ section.title }}</CardTitle>
          <CardDescription>{{ section.description }}</CardDescription>
        </CardHeader>
        <CardContent v-if="section.to">
          <Button as-child variant="outline" size="sm">
            <RouterLink :to="section.to">Open</RouterLink>
          </Button>
        </CardContent>
      </Card>
    </section>
  </div>
</template>
