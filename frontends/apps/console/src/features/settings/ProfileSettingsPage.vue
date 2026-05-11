<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {ImageUp, Trash2, Upload} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
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
        <div class="grid gap-1">
          <h1 class="text-base font-semibold">Profile</h1>
          <p class="text-sm text-muted-foreground">Manage your personal account details.</p>
        </div>
        <Button type="submit" size="sm" :disabled="!canSave">
          {{ isSaving ? "Saving..." : "Save" }}
        </Button>
      </div>



      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold">Name</h2>
          <p class="text-sm text-muted-foreground">Your name as it will be displayed</p>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="grid gap-2">
            <Label for="profile-first-name">First Name</Label>
            <Input
                id="profile-first-name"
                v-model="form.first_name"
                autocomplete="given-name"
                placeholder="Tim"
            />
          </div>
          <div class="grid gap-2">
            <Label for="profile-last-name">Last name</Label>
            <Input
                id="profile-last-name"
                v-model="form.last_name"
                autocomplete="family-name"
                placeholder="Cook"
            />
          </div>
        </div>

        <div class="grid gap-2 md:max-w-[calc(50%-0.5rem)]">
          <Label for="profile-middle-name">Middle name</Label>
          <Input
              id="profile-middle-name"
              v-model="form.middle_name"
              autocomplete="additional-name"
              placeholder="Optional"
          />
        </div>
      </section>

      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold">Email</h2>
          <p class="text-sm text-muted-foreground">The email associated to your account</p>
        </div>
        <Input :model-value="primaryEmail" readonly placeholder="No primary email"/>
      </section>

      <section class="mt-10 grid gap-4">
        <div class="grid gap-1">
          <h2 class="text-sm font-semibold">Danger zone</h2>
          <p class="text-sm text-muted-foreground">Delete account and all the associated data</p>
        </div>
        <Button class="w-fit" type="button" variant="destructive" disabled>
          Delete account
        </Button>
      </section>

      <Alert v-if="errorMessage" class="mt-6" variant="destructive">
        <AlertDescription>{{ errorMessage }}</AlertDescription>
      </Alert>
      <Alert v-if="successMessage" class="mt-6">
        <AlertDescription>{{ successMessage }}</AlertDescription>
      </Alert>
    </form>
  </SettingsLayout>
</template>
