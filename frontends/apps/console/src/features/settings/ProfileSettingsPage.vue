<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {ImageUp, Trash2, Upload} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {SettingsLayout} from "@/layouts";

const router = useRouter();
const sessionStore = useSessionStore();

const form = reactive({
  first_name: "",
  last_name: "",
  middle_name: ""
});
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const user = computed(() => sessionStore.user);
const primaryEmail = computed(() => sessionStore.primaryEmail ?? "");
const isSaving = computed(() => sessionStore.isUpdatingProfile);
const hasChanges = computed(() => {
  if (!user.value) {
    return false;
  }

  return (
      form.first_name !== user.value.first_name ||
      form.last_name !== user.value.last_name ||
      normalizeOptionalText(form.middle_name) !== user.value.middle_name
  );
});
const canSave = computed(() => (
    Boolean(user.value) &&
    form.first_name.trim().length > 0 &&
    form.last_name.trim().length > 0 &&
    hasChanges.value &&
    !isSaving.value
));

watch(
    user,
    (nextUser) => {
      if (!nextUser) {
        return;
      }

      form.first_name = nextUser.first_name;
      form.last_name = nextUser.last_name;
      form.middle_name = nextUser.middle_name ?? "";
    },
    {immediate: true}
);

onMounted(async () => {
  if (sessionStore.user) {
    return;
  }

  await sessionStore.loadCurrentUser();
  if (!sessionStore.user) {
    await router.push("/login");
  }
});

async function saveProfile() {
  if (!canSave.value) {
    return;
  }

  errorMessage.value = null;
  successMessage.value = null;

  try {
    await sessionStore.updateProfileName({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      middle_name: normalizeOptionalText(form.middle_name)
    });
    successMessage.value = "Profile updated.";
  } catch (error) {
    if (getApiErrorStatus(error) === 401) {
      sessionStore.clearSession();
      await router.push("/login");
      return;
    }

    errorMessage.value = getApiErrorMessage(error, "Could not update profile.");
  }
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}
</script>

<template>
  <SettingsLayout
      title="Profile"
      active-item="profile"
      :breadcrumbs="[{label: 'User'}, {label: 'Profile'}]"
  >
    <form class="max-w-3xl" @submit.prevent="saveProfile">
      <div class="flex items-start justify-between gap-4">
        <h1 class="text-base font-semibold text-neutral-900">Profile</h1>
        <button
            class="inline-flex h-8 items-center rounded-md bg-neutral-900 px-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
            type="submit"
            :disabled="!canSave"
        >
          {{ isSaving ? "Saving..." : "Save" }}
        </button>
      </div>

      <section class="mt-10 grid gap-4">
        <h2 class="text-sm font-semibold text-neutral-900">Picture</h2>
        <div class="flex items-start gap-4">
          <div
              class="grid size-20 place-items-center rounded-md border border-neutral-200 bg-neutral-50 text-neutral-300">
            <ImageUp class="size-6"/>
          </div>
          <div class="grid gap-3">
            <div class="flex gap-2">
              <button
                  class="inline-flex h-9 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-400"
                  type="button"
                  disabled
              >
                <Upload class="size-4"/>
                Upload
              </button>
              <button
                  class="inline-flex h-9 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-300"
                  type="button"
                  disabled
              >
                <Trash2 class="size-4"/>
                Remove
              </button>
            </div>
            <p class="text-sm text-neutral-400">We support your best PNGs, JPEGs and GIFs portraits under 10MB</p>
          </div>
        </div>
      </section>

      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold text-neutral-900">Name</h2>
          <p class="text-sm text-neutral-400">Your name as it will be displayed</p>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">First Name</span>
            <input
                v-model="form.first_name"
                class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                autocomplete="given-name"
                placeholder="Tim"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Last name</span>
            <input
                v-model="form.last_name"
                class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                autocomplete="family-name"
                placeholder="Cook"
            />
          </label>
        </div>

        <label class="grid gap-1 md:max-w-[calc(50%-0.5rem)]">
          <span class="text-xs font-semibold text-neutral-400">Middle name</span>
          <input
              v-model="form.middle_name"
              class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              autocomplete="additional-name"
              placeholder="Optional"
          />
        </label>
      </section>

      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold text-neutral-900">Email</h2>
          <p class="text-sm text-neutral-400">The email associated to your account</p>
        </div>
        <input
            class="h-9 rounded-md border border-neutral-200 bg-neutral-50 px-3 text-sm text-neutral-600 outline-none"
            :value="primaryEmail"
            readonly
            placeholder="No primary email"
        />
      </section>

      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold text-neutral-900">Danger zone</h2>
          <p class="text-sm text-neutral-400">Delete account and all the associated data</p>
        </div>
        <button
            class="inline-flex h-8 w-fit items-center rounded-md border border-red-200 bg-white px-3 text-sm font-semibold text-red-300"
            type="button"
            disabled
        >
          Delete account
        </button>
      </section>

      <p v-if="errorMessage" class="mt-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ errorMessage }}</p>
      <p v-if="successMessage" class="mt-6 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
        {{ successMessage }}
      </p>
    </form>
  </SettingsLayout>
</template>
