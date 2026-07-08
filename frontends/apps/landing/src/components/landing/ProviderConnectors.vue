<script setup lang="ts">
import type { Component } from "vue";
import { computed, ref } from "vue";
import {
  Cable,
  CircleCheck,
  Code2,
  Mail,
  MessageSquareText,
  PlugZap,
  Smartphone,
  Unplug,
  Webhook,
} from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

type Provider = {
  id: string;
  name: string;
  kind: string;
  description: string;
  throughput: string;
  contract: string;
  fields: string[];
  icon: Component;
};

const providers: Provider[] = [
  {
    id: "email",
    name: "Email",
    kind: "Transactional + marketing",
    description: "Templates, suppression lists, provider failover, and reply tracking.",
    throughput: "120k / hour",
    contract: "send(message, recipient, template, tenant)",
    fields: ["from", "templateId", "unsubscribeGroup"],
    icon: Mail,
  },
  {
    id: "sms",
    name: "SMS",
    kind: "Urgent delivery",
    description: "Short links, region routing, delivery receipts, and retry rules.",
    throughput: "34k / hour",
    contract: "send(phone, body, locale, tenant)",
    fields: ["senderId", "region", "ttl"],
    icon: MessageSquareText,
  },
  {
    id: "push",
    name: "Push",
    kind: "Mobile engagement",
    description: "Device tokens, mobile deep links, collapse keys, and quiet hours.",
    throughput: "420k / hour",
    contract: "send(device, title, payload, tenant)",
    fields: ["deviceToken", "deeplink", "collapseKey"],
    icon: Smartphone,
  },
  {
    id: "whatsapp",
    name: "WhatsApp",
    kind: "Conversational",
    description: "Approved templates, session windows, and delivery webhooks.",
    throughput: "58k / hour",
    contract: "send(contact, template, variables, tenant)",
    fields: ["templateName", "language", "conversationId"],
    icon: MessageSquareText,
  },
  {
    id: "webhook",
    name: "Webhook",
    kind: "Outbound automation",
    description: "Signed payloads into CRMs, billing systems, support tools, and data lakes.",
    throughput: "240k / hour",
    contract: "post(url, headers, payload, tenant)",
    fields: ["endpoint", "signature", "retryPolicy"],
    icon: Webhook,
  },
  {
    id: "custom",
    name: "Custom provider",
    kind: "Bring any sender",
    description: "Implement a provider adapter and expose it as a workflow action.",
    throughput: "adapter defined",
    contract: "execute(adapter, payload, tenant)",
    fields: ["adapterKey", "capabilities", "healthcheck"],
    icon: Code2,
  },
];

const selectedProviderId = ref(providers[0].id);
const connectedProviderIds = ref(["email", "push", "webhook"]);

const selectedProvider = computed(
  () => providers.find((provider) => provider.id === selectedProviderId.value) ?? providers[0],
);

const connectedCount = computed(() => connectedProviderIds.value.length);

function isConnected(id: string) {
  return connectedProviderIds.value.includes(id);
}

function selectProvider(id: string) {
  selectedProviderId.value = id;
}

function toggleProvider(id: string) {
  if (isConnected(id)) {
    connectedProviderIds.value = connectedProviderIds.value.filter(
      (providerId) => providerId !== id,
    );
    return;
  }

  connectedProviderIds.value = [...connectedProviderIds.value, id];
}
</script>

<template>
  <section id="providers" class="mx-auto w-full max-w-7xl px-5 py-16 md:px-8">
    <div class="mb-8 grid gap-5 lg:grid-cols-[0.82fr_1.18fr] lg:items-end">
      <div>
        <h2 class="text-balance text-3xl font-semibold leading-tight sm:text-4xl">
          Connect any sending provider to the same workflow contract.
        </h2>
        <p class="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          DNK treats providers as pluggable delivery adapters. Product teams can
          add a channel inside the tenant app while the runtime keeps retries,
          payloads, and statistics consistent.
        </p>
      </div>

      <div class="rounded-2xl border border-border bg-white p-4">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm font-semibold">Provider mesh</p>
            <p class="mt-1 text-xs text-muted-foreground">
              {{ connectedCount }} connected channels route into workflow actions.
            </p>
          </div>
          <Badge variant="success">{{ connectedCount }}/{{ providers.length }} online</Badge>
        </div>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[1.16fr_0.84fr]">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card
          v-for="provider in providers"
          :key="provider.id"
          :data-testid="`provider-${provider.id}`"
          :class="
            cn(
              'provider-card cursor-pointer rounded-2xl py-5 outline-none transition-all',
              selectedProviderId === provider.id && 'provider-card-selected',
            )
          "
          role="button"
          tabindex="0"
          @click="selectProvider(provider.id)"
          @keydown.enter.prevent="selectProvider(provider.id)"
          @keydown.space.prevent="selectProvider(provider.id)"
        >
          <CardHeader class="px-5">
            <div class="flex items-start justify-between gap-3">
              <div class="flex size-10 items-center justify-center rounded-lg border border-border bg-secondary">
                <component :is="provider.icon" class="size-4" aria-hidden="true" />
              </div>
              <Badge :variant="isConnected(provider.id) ? 'success' : 'outline'">
                {{ isConnected(provider.id) ? "Connected" : "Ready" }}
              </Badge>
            </div>
            <CardTitle class="pt-2 text-base">{{ provider.name }}</CardTitle>
            <CardDescription class="leading-6">
              {{ provider.kind }}
            </CardDescription>
          </CardHeader>
          <CardContent class="grid gap-3 px-5">
            <p class="text-sm leading-6 text-muted-foreground">
              {{ provider.description }}
            </p>
            <div class="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-xs">
              <span class="text-muted-foreground">Throughput</span>
              <span class="font-semibold">{{ provider.throughput }}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card class="self-start rounded-2xl py-5">
        <CardHeader class="px-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <CardTitle class="text-xl">{{ selectedProvider.name }} adapter</CardTitle>
              <CardDescription class="mt-2 leading-6">
                Select a provider to preview the normalized runtime contract.
              </CardDescription>
            </div>
            <div class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Cable class="size-5" aria-hidden="true" />
            </div>
          </div>
        </CardHeader>
        <CardContent class="grid gap-5 px-5">
          <div class="rounded-xl border border-border bg-muted/55 p-4">
            <p class="text-xs font-medium uppercase text-muted-foreground">Action contract</p>
            <p class="mt-2 break-words font-mono text-sm leading-6">
              {{ selectedProvider.contract }}
            </p>
          </div>

          <div>
            <p class="text-sm font-semibold">Mapped fields</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <Badge
                v-for="field in selectedProvider.fields"
                :key="field"
                variant="outline"
              >
                {{ field }}
              </Badge>
            </div>
          </div>

          <Separator />

          <div class="grid gap-3">
            <div class="flex items-center gap-3 rounded-xl bg-muted p-3">
              <CircleCheck class="size-4 text-teal-600" aria-hidden="true" />
              <span class="text-sm">Tenant secrets remain scoped per environment.</span>
            </div>
            <div class="flex items-center gap-3 rounded-xl bg-muted p-3">
              <PlugZap class="size-4 text-sky-600" aria-hidden="true" />
              <span class="text-sm">Every adapter emits attempts, receipts, and errors.</span>
            </div>
          </div>

          <Button
            data-testid="provider-connect-toggle"
            type="button"
            :variant="isConnected(selectedProvider.id) ? 'secondary' : 'default'"
            @click="toggleProvider(selectedProvider.id)"
          >
            <Unplug
              v-if="isConnected(selectedProvider.id)"
              data-icon="inline-start"
              aria-hidden="true"
            />
            <PlugZap v-else data-icon="inline-start" aria-hidden="true" />
            {{ isConnected(selectedProvider.id) ? "Disconnect adapter" : "Connect adapter" }}
          </Button>
        </CardContent>
      </Card>
    </div>
  </section>
</template>
