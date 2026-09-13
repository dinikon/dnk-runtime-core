<script setup lang="ts">
import { onMounted, ref } from "vue";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { useUserStore } from "@/app/stores/user";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { accessApi, type Member, type Invitation, type Role } from "../api";

const userStore = useUserStore();
const members = ref<Member[]>([]);
const invitations = ref<Invitation[]>([]);
const email = ref("");
const role = ref<Role>("member");
const invitationUrl = ref("");
const error = ref("");
const busy = ref(false);
const loading = ref(true);

async function load() {
  [members.value, invitations.value] = await Promise.all([
    accessApi.members(),
    accessApi.invitations(),
  ]);
}
async function run(action: () => Promise<unknown>) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await action();
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "The change could not be saved. Please try again.",
    );
  } finally {
    busy.value = false;
  }
}
async function invite() {
  invitationUrl.value = "";
  await run(async () => {
    invitationUrl.value = (
      await accessApi.invite(email.value.trim(), role.value)
    ).invitation_url;
    email.value = "";
  });
}
async function copyLink() {
  try {
    await navigator.clipboard.writeText(invitationUrl.value);
    toast.success("Invitation link copied");
  } catch {
    error.value = "Select the invitation link below and copy it manually.";
  }
}
onMounted(async () => {
  try {
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      "You need administrator access to manage members.",
    );
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="flex min-h-0 flex-col gap-6 overflow-y-auto pb-6">
    <div>
      <h1 class="text-2xl font-semibold">Members & invitations</h1>
      <p class="text-muted-foreground">Manage who can access this workspace.</p>
    </div>
    <Alert v-if="error" variant="destructive" role="alert"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <p v-if="loading" role="status">Loading members…</p>
    <template v-else-if="userStore.user?.role === 'admin'">
      <Card>
        <CardHeader
          ><CardTitle>Invite a member</CardTitle
          ><CardDescription
            >Share a private link. The recipient verifies this email before
            joining. Links expire after 7 days.</CardDescription
          ></CardHeader
        >
        <CardContent class="flex flex-col gap-4">
          <form @submit.prevent="invite">
            <FieldGroup class="md:flex-row md:items-end">
              <Field
                ><FieldLabel for="invite-email">Email</FieldLabel
                ><Input
                  id="invite-email"
                  v-model="email"
                  type="email"
                  autocomplete="email"
                  required
                  :disabled="busy"
              /></Field>
              <Field class="md:max-w-40"
                ><FieldLabel for="invite-role">Role</FieldLabel
                ><Select v-model="role" :disabled="busy"
                  ><SelectTrigger id="invite-role"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem value="member">Member</SelectItem
                      ><SelectItem value="admin">Admin</SelectItem></SelectGroup
                    ></SelectContent
                  ></Select
                ></Field
              >
              <Button type="submit" :disabled="busy">{{
                busy ? "Saving…" : "Create invitation"
              }}</Button>
            </FieldGroup>
          </form>
          <Field v-if="invitationUrl"
            ><FieldLabel for="invitation-link"
              >Invitation link — copy it before leaving this page</FieldLabel
            >
            <div class="flex gap-2">
              <Input
                id="invitation-link"
                :model-value="invitationUrl"
                readonly
              /><Button variant="outline" @click="copyLink">Copy link</Button>
            </div></Field
          >
        </CardContent>
      </Card>
      <Card>
        <CardHeader
          ><CardTitle>Members</CardTitle
          ><CardDescription
            >Revoking access signs the member out of this
            workspace.</CardDescription
          ></CardHeader
        >
        <CardContent>
          <Table
            ><TableHeader
              ><TableRow
                ><TableHead>Member</TableHead><TableHead>Role</TableHead
                ><TableHead>Cloud account</TableHead
                ><TableHead>Access</TableHead
                ><TableHead
                  ><span class="sr-only">Actions</span></TableHead
                ></TableRow
              ></TableHeader
            >
            <TableBody
              ><TableRow v-for="member in members" :key="member.id">
                <TableCell
                  ><div class="font-medium">
                    {{
                      [member.first_name, member.last_name]
                        .filter(Boolean)
                        .join(" ") || member.email
                    }}
                  </div>
                  <div class="text-sm text-muted-foreground">
                    {{ member.email }}
                  </div></TableCell
                >
                <TableCell
                  ><Select
                    :model-value="member.role"
                    :disabled="busy"
                    @update:model-value="
                      (value) =>
                        run(() =>
                          accessApi.updateMember(member.id, {
                            role: value as Role,
                          }),
                        )
                    "
                    ><SelectTrigger :aria-label="`Role for ${member.email}`"
                      ><SelectValue /></SelectTrigger
                    ><SelectContent
                      ><SelectGroup
                        ><SelectItem value="member">Member</SelectItem
                        ><SelectItem value="admin"
                          >Admin</SelectItem
                        ></SelectGroup
                      ></SelectContent
                    ></Select
                  ></TableCell
                >
                <TableCell>{{
                  member.cloud_linked ? "Linked" : "Not linked"
                }}</TableCell
                ><TableCell
                  ><Badge
                    :variant="
                      member.status === 'active' ? 'secondary' : 'outline'
                    "
                    >{{
                      member.status === "active" ? "Active" : "Revoked"
                    }}</Badge
                  ></TableCell
                >
                <TableCell
                  ><Button
                    variant="outline"
                    size="sm"
                    :disabled="busy"
                    @click="
                      run(() =>
                        accessApi.updateMember(member.id, {
                          status:
                            member.status === 'active' ? 'revoked' : 'active',
                        }),
                      )
                    "
                    >{{
                      member.status === "active"
                        ? "Revoke access"
                        : "Restore access"
                    }}</Button
                  ></TableCell
                >
              </TableRow></TableBody
            >
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader
          ><CardTitle>Invitations</CardTitle
          ><CardDescription
            >Accepted and revoked invitations remain in the
            history.</CardDescription
          ></CardHeader
        >
        <CardContent
          ><p v-if="!invitations.length" class="text-sm text-muted-foreground">
            No invitations yet.
          </p>
          <Table v-else
            ><TableHeader
              ><TableRow
                ><TableHead>Email</TableHead><TableHead>Role</TableHead
                ><TableHead>Status</TableHead><TableHead>Expires</TableHead
                ><TableHead
                  ><span class="sr-only">Actions</span></TableHead
                ></TableRow
              ></TableHeader
            ><TableBody
              ><TableRow v-for="invitation in invitations" :key="invitation.id"
                ><TableCell>{{ invitation.email }}</TableCell
                ><TableCell>{{ invitation.role }}</TableCell
                ><TableCell>{{ invitation.state }}</TableCell
                ><TableCell>{{
                  new Date(invitation.expires_at).toLocaleDateString()
                }}</TableCell
                ><TableCell
                  ><Button
                    v-if="invitation.state === 'pending'"
                    variant="outline"
                    size="sm"
                    :disabled="busy"
                    @click="
                      run(() => accessApi.revokeInvitation(invitation.id))
                    "
                    >Revoke invitation</Button
                  ></TableCell
                ></TableRow
              ></TableBody
            ></Table
          ></CardContent
        >
      </Card>
    </template>
  </div>
</template>
