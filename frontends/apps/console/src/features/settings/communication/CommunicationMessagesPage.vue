<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";
import {Loader2, RefreshCcw} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {communicationApi, type OutboundMessage} from "@/api/communication";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {SettingsLayout} from "@/layouts";

const router = useRouter();
const sessionStore = useSessionStore();

const messages = ref<OutboundMessage[]>([]);
const isLoading = ref(false);
const pageError = ref<string | null>(null);

const statusCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const message of messages.value) {
    counts[message.internal_status] = (counts[message.internal_status] ?? 0) + 1;
  }
  return Object.entries(counts).sort(([left], [right]) => left.localeCompare(right));
});

onMounted(() => {
  void loadMessages();
});

async function loadMessages() {
  isLoading.value = true;
  pageError.value = null;

  try {
    messages.value = (await communicationApi.listMessages()).items;
  } catch (error) {
    if (getApiErrorStatus(error) === 401) {
      sessionStore.clearSession();
      await router.push("/login");
      return;
    }

    pageError.value = getApiErrorMessage(error, "Could not load messages.");
  } finally {
    isLoading.value = false;
  }
}

function shortId(value: string): string {
  return value.slice(0, 8);
}

function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function statusClass(status: string): string {
  if (status === "FAILED" || status === "EXPIRED" || status === "UNDELIVERED") {
    return "bg-destructive/10 text-destructive ring-destructive/20";
  }
  if (status === "DELIVERED" || status === "SENT") {
    return "bg-emerald-500/10 text-emerald-700 ring-emerald-500/20";
  }
  return "bg-muted text-muted-foreground ring-border";
}
</script>

<template>
  <SettingsLayout
      title="Communication Messages"
      active-item="communication-messages"
      :breadcrumbs="[{label: 'Workspace'}, {label: 'Communication'}, {label: 'Messages'}]"
  >
    <div class="flex min-h-[560px] flex-col">
      <header class="flex items-start justify-between gap-4">
        <div class="grid gap-1">
          <h1 class="text-base font-semibold">Messages</h1>
          <p class="text-sm text-muted-foreground">Outbound message history and provider status snapshots</p>
        </div>
        <Button type="button" variant="outline" size="sm" @click="loadMessages">
          <RefreshCcw class="size-4"/>
          Refresh
        </Button>
      </header>

      <Alert v-if="pageError" class="mt-5" variant="destructive">
        <AlertDescription>{{ pageError }}</AlertDescription>
      </Alert>

      <div v-if="statusCounts.length > 0" class="mt-6 flex flex-wrap gap-2">
        <span
            v-for="[status, count] in statusCounts"
            :key="status"
            class="inline-flex items-center rounded px-2 py-1 text-xs font-semibold ring-1"
            :class="statusClass(status)"
        >
          {{ status }} {{ count }}
        </span>
      </div>

      <div class="mt-4 overflow-hidden rounded-md border">
        <table class="w-full border-collapse text-left text-sm">
          <thead class="bg-background text-xs font-semibold text-muted-foreground">
          <tr class="border-b">
            <th class="px-3 py-2">Message</th>
            <th class="px-3 py-2">Recipient</th>
            <th class="px-3 py-2">Channel</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">External</th>
            <th class="px-3 py-2">Created</th>
          </tr>
          </thead>
          <tbody>
          <tr v-if="isLoading">
            <td colspan="6" class="px-3 py-10 text-center text-muted-foreground">
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin"/>
                Loading messages...
              </span>
            </td>
          </tr>
          <tr v-else-if="messages.length === 0">
            <td colspan="6" class="px-3 py-10 text-center text-muted-foreground">No messages.</td>
          </tr>
          <tr v-for="message in messages" v-else :key="message.outbound_message_id" class="border-b last:border-b-0">
            <td class="px-3 py-2 font-mono text-xs">{{ shortId(message.outbound_message_id) }}</td>
            <td class="px-3 py-2">{{ message.recipient_address }}</td>
            <td class="px-3 py-2 text-muted-foreground">{{ message.channel_code }}</td>
            <td class="px-3 py-2">
              <span class="inline-flex items-center rounded px-2 py-1 text-xs font-semibold ring-1"
                    :class="statusClass(message.internal_status)">
                {{ message.internal_status }}
              </span>
            </td>
            <td class="px-3 py-2">
              <div class="font-mono text-xs">{{ message.external_message_id ?? "—" }}</div>
              <div class="text-xs text-muted-foreground">{{ message.external_status ?? "—" }}</div>
            </td>
            <td class="px-3 py-2 text-muted-foreground">{{ formatDate(message.created_at) }}</td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>
  </SettingsLayout>
</template>
