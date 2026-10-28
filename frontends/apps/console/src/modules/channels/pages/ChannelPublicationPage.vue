<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useChannel } from "../model/channel.queries";
import { usePublication } from "../model/publication.queries";
import { usePublicationsPageState } from "../model/use-publications-page-state";
import { channelErrorMessage } from "../model/channel.errors";
import PublicationsToolbar from "../ui/PublicationsToolbar.vue";
import { bindingPublicationPositions } from "../model/bindings/binding.matching";
import CatalogBindingsPage from "./CatalogBindingsPage.vue";
import PublicationDetailsBody from "../ui/PublicationDetailsBody.vue";
const route = useRoute(),
  router = useRouter();
const id = computed(() => String(route.params.id ?? "")),
  publicationId = computed(() => String(route.params.publicationId ?? ""));
const channel = useChannel(id),
  state = usePublicationsPageState(channel.data),
  locale = computed(() => state.filters.value.locale),
  publication = usePublication(id, publicationId, locale);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header>
      <Button
        variant="link"
        class="px-0"
        @click="
          router.push({
            name: 'channel-publications',
            params: { id },
            query: route.query,
          })
        "
        >Все публикации</Button
      >
      <h1 class="text-2xl font-semibold">
        {{ channel.data.value?.name ?? "Публикация" }}
      </h1>
    </header>
    <PublicationsToolbar
      search=""
      :locale="publication.data.value?.locale ?? locale"
      :locales="publication.data.value?.locales ?? []"
      @search="
        router.push({
          name: 'channel-publications',
          params: { id },
          query: { q: $event, locale },
        })
      "
      @locale="state.setLocale"
    />
    <PublicationDetailsBody
      :card="publication.data.value?.card"
      :pending="publication.isPending.value"
      :error="
        publication.error.value
          ? channelErrorMessage(publication.error.value)
          : ''
      "
      @retry="publication.refetch()"
      :requested-publication-id="publicationId"
    />
    <CatalogBindingsPage
      v-if="publication.data.value"
      :key="`${id}:${publication.data.value.card.id}`"
      :channel-id="id"
      :publication-id="publication.data.value.card.id"
      :initial-publications="
        bindingPublicationPositions(publication.data.value.card)
      "
      :publication-has-variants="
        publication.data.value.card.rootKind === 'variable' ||
        publication.data.value.card.items.some((v) => v.kind === 'variant')
      "
      :locale="locale"
    />
  </div>
</template>
