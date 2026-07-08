<script setup lang="ts">
import { ServerCog } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import CrmWorkflowChains from "@/components/landing/CrmWorkflowChains.vue";
import CustomTables from "@/components/landing/CustomTables.vue";
import EventIngestion from "@/components/landing/EventIngestion.vue";
import HeroBlock from "@/components/landing/HeroBlock.vue";
import ProjectDescription from "@/components/landing/ProjectDescription.vue";
import ProviderConnectors from "@/components/landing/ProviderConnectors.vue";
import WorkflowDemo from "@/components/landing/WorkflowDemo.vue";
</script>

<template>
  <main class="landing-shell min-h-screen overflow-hidden">
    <header class="sticky top-0 z-20 border-b border-border/70 bg-white/82 backdrop-blur-xl">
      <div class="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-5 px-5 md:px-8">
        <a href="#" class="flex items-center gap-3 font-semibold" aria-label="DNK home">
          <span class="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ServerCog class="size-4" aria-hidden="true" />
          </span>
          <span class="text-base">DNK</span>
        </a>

        <nav class="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex" aria-label="Main navigation">
          <a class="transition-colors hover:text-foreground" href="#product">Product</a>
          <a class="transition-colors hover:text-foreground" href="#workflow">Demo</a>
          <a class="transition-colors hover:text-foreground" href="#crm-workflows">CRM</a>
          <a class="transition-colors hover:text-foreground" href="#providers">Providers</a>
          <a class="transition-colors hover:text-foreground" href="#events">Events</a>
          <a class="transition-colors hover:text-foreground" href="#tables">Tables</a>
          <a class="transition-colors hover:text-foreground" href="#project">Runtime</a>
        </nav>

        <Button as="a" href="https://admin.dniko.net" size="sm">
          Open console
        </Button>
      </div>
    </header>

    <HeroBlock id="product" />
    <WorkflowDemo />
    <CrmWorkflowChains />
    <ProviderConnectors />
    <EventIngestion />
    <CustomTables />
    <ProjectDescription />
  </main>
</template>
