<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

const route = useRoute();
const isDetailRoute = computed(() => route.name === "broadcast-detail");
</script>

<template>
  <div class="flex min-w-0 flex-1 items-center justify-between gap-3">
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem class="hidden md:block">
          <BreadcrumbLink as-child>
            <RouterLink to="/dashboard">Workspace</RouterLink>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator class="hidden md:block" />
        <BreadcrumbItem class="hidden md:block">
          <BreadcrumbLink as-child>
            <RouterLink to="/cdp/broadcasts">CDP</RouterLink>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator class="hidden md:block" />
        <BreadcrumbItem v-if="isDetailRoute" class="hidden md:block">
          <BreadcrumbLink as-child>
            <RouterLink to="/cdp/broadcasts">Broadcasts</RouterLink>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator v-if="isDetailRoute" class="hidden md:block" />
        <BreadcrumbItem>
          <BreadcrumbPage>
            {{ isDetailRoute ? "Broadcast detail" : "Broadcasts" }}
          </BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  </div>
</template>
