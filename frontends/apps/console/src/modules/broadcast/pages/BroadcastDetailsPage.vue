<script setup lang="ts">
import { computed } from "vue";
import { isAxiosError } from "axios";
import { ArrowLeft, RefreshCcw, UploadCloud } from "lucide-vue-next";
import { RouterLink, useRoute } from "vue-router";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBroadcastQuery } from "@/modules/broadcast/queries/use-broadcast-query";
import {
  apiErrorMessage,
  formatBroadcastDate,
  shortBroadcastId,
} from "@/modules/broadcast/util";

const route = useRoute();
const broadcastId = computed(() => {
  const id = route.params.id;
  return Array.isArray(id) ? (id[0] ?? "") : (id ?? "");
});
const hasBroadcastId = computed(() => broadcastId.value.length > 0);
const broadcastQuery = useBroadcastQuery(broadcastId, hasBroadcastId);
const broadcast = computed(() => broadcastQuery.data.value);
const isNotFound = computed(
  () =>
    isAxiosError(broadcastQuery.error.value) &&
    broadcastQuery.error.value.response?.status === 404,
);
const backToList = computed(() => ({
  name: "broadcasts",
  query: route.query,
}));
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <div class="flex min-w-0 items-start gap-3">
        <Button type="button" variant="outline" size="icon" as-child>
          <RouterLink :to="backToList" aria-label="Back to broadcasts">
            <ArrowLeft class="size-4" />
          </RouterLink>
        </Button>
        <div class="grid min-w-0 gap-1">
          <div class="flex min-w-0 flex-wrap items-center gap-2">
            <h2 class="truncate text-lg font-semibold tracking-normal">
              {{ broadcast?.title ?? "Broadcast" }}
            </h2>
            <Badge v-if="broadcast" variant="outline">
              {{ broadcast.status }}
            </Badge>
          </div>
          <p class="text-sm text-muted-foreground">
            {{ broadcast ? shortBroadcastId(broadcast.id) : broadcastId }}
          </p>
        </div>
      </div>

      <Button
        type="button"
        variant="outline"
        :disabled="broadcastQuery.isFetching.value || !hasBroadcastId"
        @click="broadcastQuery.refetch()"
      >
        <RefreshCcw
          class="size-4"
          :class="{ 'animate-spin': broadcastQuery.isFetching.value }"
        />
        Refresh
      </Button>
    </div>

    <Alert v-if="!hasBroadcastId" variant="destructive">
      <AlertDescription>Broadcast id is missing.</AlertDescription>
    </Alert>
    <Alert v-else-if="isNotFound" variant="destructive">
      <AlertDescription>Broadcast not found.</AlertDescription>
    </Alert>
    <Alert v-else-if="broadcastQuery.error.value" variant="destructive">
      <AlertDescription>
        {{ apiErrorMessage(broadcastQuery.error.value) }}
      </AlertDescription>
    </Alert>

    <template v-if="broadcastQuery.isLoading.value">
      <Card>
        <CardHeader>
          <Skeleton class="h-6 w-56" />
          <Skeleton class="h-4 w-80" />
        </CardHeader>
        <CardContent class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Skeleton class="h-16 w-full" />
          <Skeleton class="h-16 w-full" />
          <Skeleton class="h-16 w-full" />
          <Skeleton class="h-16 w-full" />
        </CardContent>
      </Card>
    </template>

    <template v-else-if="broadcast">
      <Card>
        <CardHeader>
          <CardTitle>{{ broadcast.title }}</CardTitle>
          <CardDescription>
            {{ broadcast.description ?? "No description." }}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div class="grid gap-1 rounded-md border p-3">
              <dt class="text-xs font-medium uppercase text-muted-foreground">
                Status
              </dt>
              <dd>
                <Badge variant="outline">{{ broadcast.status }}</Badge>
              </dd>
            </div>
            <div class="grid gap-1 rounded-md border p-3">
              <dt class="text-xs font-medium uppercase text-muted-foreground">
                ID
              </dt>
              <dd class="break-all text-sm">{{ broadcast.id }}</dd>
            </div>
            <div class="grid gap-1 rounded-md border p-3">
              <dt class="text-xs font-medium uppercase text-muted-foreground">
                Created
              </dt>
              <dd class="text-sm">
                {{ formatBroadcastDate(broadcast.created_at) }}
              </dd>
            </div>
            <div class="grid gap-1 rounded-md border p-3">
              <dt class="text-xs font-medium uppercase text-muted-foreground">
                Updated
              </dt>
              <dd class="text-sm">
                {{ formatBroadcastDate(broadcast.updated_at) }}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audience</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            class="flex min-h-48 flex-col items-center justify-center gap-3 rounded-md border border-dashed bg-muted/20 p-6 text-center"
          >
            <UploadCloud class="size-8 text-muted-foreground" />
            <p class="max-w-md text-sm text-muted-foreground">
              Audience import will be configured here.
            </p>
          </div>
        </CardContent>
      </Card>
    </template>
  </section>
</template>
