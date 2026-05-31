<script lang="ts">
export const description = "An inset sidebar with secondary navigation.";
export const iframeHeight = "800px";
</script>

<script setup lang="ts">
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { useCurrentUserQuery } from "@/modules/auth/queries/use-current-user-query";
import WorkspaceSidebar from "./components/WorkspaceSidebar.vue";

useCurrentUserQuery();
</script>

<template>
  <SidebarProvider>
    <WorkspaceSidebar />
    <SidebarInset>
      <header class="flex h-16 shrink-0 items-center gap-2">
        <div class="flex items-center gap-2 px-4">
          <SidebarTrigger class="-ml-1" />
          <Separator
            orientation="vertical"
            class="mr-2 data-[orientation=vertical]:h-4"
          />
          <RouterView name="header" />
        </div>
      </header>
      <div class="flex flex-1 flex-col gap-4 p-4 pt-0">
        <RouterView />
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
