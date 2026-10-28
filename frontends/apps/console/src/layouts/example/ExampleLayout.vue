<script setup lang="ts">
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import ExampleSidebar from "./components/ExampleSidebar.vue";
</script>

<template>
  <SidebarProvider>
    <ExampleSidebar />
    <SidebarInset
      class="h-svh min-h-0 overflow-hidden md:h-[calc(100svh-1rem)]"
    >
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
      <main class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4 pt-0">
        <RouterView />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>
