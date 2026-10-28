import { parsePublicationFilters } from "../publication.filters";
import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
export function useBindingsPageState(): {
  groupId: ComputedRef<string>;
  channelId: ComputedRef<string>;
  offset: ComputedRef<number>;
  limit: ComputedRef<number>;
  open: (id: string, channel: string) => Promise<void>;
  close: () => Promise<void>;
  paginate: (page: number, limit: number) => Promise<void>;
} {
  const route = useRoute(),
    router = useRouter();
  const groupId = computed(() =>
    typeof route.query.binding === "string" ? route.query.binding : "",
  );
  const channelId = computed(() =>
    typeof route.query.binding_channel === "string"
      ? route.query.binding_channel
      : "",
  );
  const pagination = computed(() =>
    parsePublicationFilters({
      limit: route.query.binding_limit,
      offset: route.query.binding_offset,
    }),
  );
  const limit = computed(() => pagination.value.limit),
    offset = computed(() => pagination.value.offset);
  return {
    groupId,
    channelId,
    limit,
    offset,
    open: async (id, channel) => {
      await router.replace({
        query: {
          ...route.query,
          binding: id,
          binding_channel: channel || undefined,
        },
      });
    },
    close: async () => {
      await router.replace({
        query: {
          ...route.query,
          binding: undefined,
          binding_channel: undefined,
        },
      });
    },
    paginate: async (page, size) => {
      await router.replace({
        query: {
          ...route.query,
          binding_offset: (page - 1) * size || undefined,
          binding_limit: size === 25 ? undefined : size,
        },
      });
    },
  };
}
