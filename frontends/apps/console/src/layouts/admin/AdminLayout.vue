<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { adminNavigation } from "@/app/navigation/admin-navigation";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import AdminSidebar from "./components/AdminSidebar.vue";

const route = useRoute();
const pageTitle = computed(
  () =>
    adminNavigation
      .flatMap((group) => group.items)
      .find((item) => item.url === route.path)?.title ?? "Настройки",
);
</script>

<template>
  <SidebarProvider>
    <AdminSidebar />
    <SidebarInset
      class="h-svh min-h-0 overflow-hidden md:h-[calc(100svh-1rem)]"
    >
      <header class="flex h-16 shrink-0 items-center border-b md:border-b-0">
        <div class="flex items-center gap-2 px-4">
          <SidebarTrigger class="-ml-1" />
          <Separator
            orientation="vertical"
            class="mr-2 data-[orientation=vertical]:h-4"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage class="text-muted-foreground"
                  >Настройки</BreadcrumbPage
                >
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{{ pageTitle }}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </header>
      <main class="flex min-h-0 flex-1 flex-col overflow-hidden p-4 pt-0">
        <RouterView />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>
