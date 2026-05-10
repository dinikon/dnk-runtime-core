<script setup lang="ts">
import {computed, reactive, watch} from "vue";
import {PanelRightClose, Save, Trash2, X} from "lucide-vue-next";

import type {ContactTableRow} from "@/components/app/table";
import type {ContactFieldOption} from "@/shared/api/crm";
import type {ContactFormValue} from "@/components/app/details/types";

const props = defineProps<{
  row: ContactTableRow;
  statusOptions: ContactFieldOption[];
  tagOptions: ContactFieldOption[];
  isSaving: boolean;
  isDeleting: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  close: [];
  save: [value: ContactFormValue];
  delete: [];
}>();

const form = reactive<ContactFormValue>({
  first_name: "",
  last_name: null,
  middle_name: null,
  status: null,
  tags: []
});

const title = computed(() => {
  const name = [form.first_name, form.last_name].filter(Boolean).join(" ").trim();
  return name || (props.row.isDraft ? "New contact" : "Contact details");
});

const canSave = computed(() => form.first_name.trim().length > 0 && !props.isSaving);

watch(
    () => props.row.key,
    () => {
      form.first_name = props.row.firstName;
      form.last_name = props.row.lastName;
      form.middle_name = props.row.middleName;
      form.status = props.row.status;
      form.tags = [...props.row.tags];
    },
    {immediate: true}
);

function save() {
  if (!canSave.value) {
    return;
  }

  emit("save", {
    first_name: form.first_name.trim(),
    last_name: normalizeOptionalText(form.last_name),
    middle_name: normalizeOptionalText(form.middle_name),
    status: normalizeOptionalText(form.status),
    tags: form.tags
  });
}

function toggleTag(tag: string) {
  form.tags = form.tags.includes(tag)
      ? form.tags.filter((item) => item !== tag)
      : [...form.tags, tag];
}

function normalizeOptionalText(value: string | null): string | null {
  const normalized = value?.trim() ?? "";
  return normalized.length > 0 ? normalized : null;
}
</script>

<template>
  <aside class="flex h-full min-w-0 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm">
    <header class="flex min-h-14 items-center gap-2 border-b border-neutral-200 px-4">
      <button
          class="grid size-8 place-items-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          type="button"
          title="Close"
          @click="$emit('close')"
      >
        <X class="size-4"/>
      </button>
      <div class="grid size-8 place-items-center rounded-md bg-neutral-100 text-neutral-500">
        <PanelRightClose class="size-4"/>
      </div>
      <div class="min-w-0">
        <h2 class="truncate text-sm font-semibold text-neutral-900">{{ title }}</h2>
        <p class="text-xs text-neutral-400">{{ row.isDraft ? "Draft contact" : "Contact" }}</p>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-auto px-6 py-6">
      <div class="grid gap-5">
        <label class="grid gap-1.5">
          <span class="text-xs font-semibold text-neutral-500">First name</span>
          <input
              v-model="form.first_name"
              class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Required"
          />
        </label>

        <label class="grid gap-1.5">
          <span class="text-xs font-semibold text-neutral-500">Last name</span>
          <input
              v-model="form.last_name"
              class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Optional"
          />
        </label>

        <label class="grid gap-1.5">
          <span class="text-xs font-semibold text-neutral-500">Middle name</span>
          <input
              v-model="form.middle_name"
              class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Optional"
          />
        </label>

        <label class="grid gap-1.5">
          <span class="text-xs font-semibold text-neutral-500">Status</span>
          <select
              v-model="form.status"
              class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
          >
            <option :value="null">No status</option>
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <section class="grid gap-2">
          <span class="text-xs font-semibold text-neutral-500">Tags</span>
          <div class="flex flex-wrap gap-2">
            <button
                v-for="option in tagOptions"
                :key="option.value"
                type="button"
                class="rounded-full border px-3 py-1 text-xs font-medium transition-colors"
                :class="form.tags.includes(option.value)
                ? 'border-neutral-900 bg-neutral-900 text-white'
                : 'border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50'"
                @click="toggleTag(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <p v-if="tagOptions.length === 0" class="text-sm text-neutral-400">No tag options configured.</p>
        </section>

        <p v-if="error" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </div>
    </div>

    <footer class="flex min-h-14 items-center justify-between gap-3 border-t border-neutral-200 px-4">
      <button
          v-if="!row.isDraft"
          class="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-sm font-medium text-red-600 hover:bg-red-50"
          type="button"
          :disabled="isDeleting"
          @click="$emit('delete')"
      >
        <Trash2 class="size-4"/>
        {{ isDeleting ? "Deleting..." : "Delete" }}
      </button>
      <span v-else/>

      <button
          class="inline-flex h-8 items-center gap-1.5 rounded-md bg-neutral-900 px-3 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          type="button"
          :disabled="!canSave"
          @click="save"
      >
        <Save class="size-4"/>
        {{ isSaving ? "Saving..." : "Save" }}
      </button>
    </footer>
  </aside>
</template>
