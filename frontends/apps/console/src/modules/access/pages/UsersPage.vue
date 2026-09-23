<script setup lang="ts">
import { computed, ref } from "vue";

import { getApiErrorMessage } from "@/app/providers/http";
import {
  useInviteMemberMutation,
  useRevokeInvitationMutation,
  useUpdateMemberMutation,
} from "../model/use-access-mutations";
import { useInvitationsQuery } from "../model/use-invitations-query";
import { useMembersQuery } from "../model/use-members-query";
import { useUsersPageState } from "../model/use-users-page-state";
import type {
  Invitation,
  InvitationInput,
  InvitationResult,
  Member,
  MemberUpdate,
} from "../model/access.types";
import ConfirmAccessActionDialog from "../ui/common/ConfirmAccessActionDialog.vue";
import UsersCollectionBody from "../ui/common/UsersCollectionBody.vue";
import UsersTabs from "../ui/common/UsersTabs.vue";
import UsersToolbar from "../ui/common/UsersToolbar.vue";
import InvitationResultsDialog from "../ui/invitations/InvitationResultsDialog.vue";
import InvitationsTable from "../ui/invitations/InvitationsTable.vue";
import InviteUsersPanel from "../ui/invitations/InviteUsersPanel.vue";
import ManageMemberDialog from "../ui/members/ManageMemberDialog.vue";
import MembersTable from "../ui/members/MembersTable.vue";
import UsersHeader from "../ui/page/UsersHeader.vue";

const membersQuery = useMembersQuery();
const invitationsQuery = useInvitationsQuery();
const inviteMutation = useInviteMemberMutation();
const updateMemberMutation = useUpdateMemberMutation();
const revokeInvitationMutation = useRevokeInvitationMutation();
const { role, search, status, tab } = useUsersPageState();

const managingMember = ref<Member | null>(null);
const memberUpdateError = ref("");
const revokingInvitation = ref<Invitation | null>(null);
const invitationActionError = ref("");
const inviteResults = ref<InvitationResult[]>([]);
const resultsOpen = ref(false);
const inviteResetKey = ref(0);

const members = computed(() => membersQuery.data.value ?? []);
const invitations = computed(() => invitationsQuery.data.value ?? []);
const pendingInvitationCount = computed(
  () => invitations.value.filter((item) => item.state === "pending").length,
);
const activeAdminCount = computed(
  () =>
    members.value.filter(
      (member) => member.role === "admin" && member.status === "active",
    ).length,
);

const normalizedSearch = computed(() => search.value.trim().toLowerCase());
const filteredMembers = computed(() =>
  members.value.filter((member) => {
    const matchesSearch =
      !normalizedSearch.value ||
      member.displayName.toLowerCase().includes(normalizedSearch.value) ||
      member.email.toLowerCase().includes(normalizedSearch.value);
    const matchesRole = role.value === "all" || member.role === role.value;
    const matchesStatus =
      status.value === "all" || member.status === status.value;
    return matchesSearch && matchesRole && matchesStatus;
  }),
);
const filteredInvitations = computed(() =>
  invitations.value.filter((invitation) => {
    const matchesSearch =
      !normalizedSearch.value ||
      invitation.email.toLowerCase().includes(normalizedSearch.value);
    const matchesRole = role.value === "all" || invitation.role === role.value;
    const matchesStatus =
      status.value === "all" || invitation.state === status.value;
    return matchesSearch && matchesRole && matchesStatus;
  }),
);

async function inviteUsers(items: InvitationInput[]) {
  const results: InvitationResult[] = [];
  for (const item of items) {
    try {
      const result = await inviteMutation.mutateAsync(item);
      results.push({
        ...item,
        ok: true,
        invitationUrl: result.invitationUrl,
      });
    } catch (error) {
      results.push({
        ...item,
        ok: false,
        message: getApiErrorMessage(error, "Не удалось создать приглашение."),
      });
    }
  }
  inviteResults.value = results;
  inviteResetKey.value += 1;
  resultsOpen.value = true;
}

function openMember(member: Member) {
  memberUpdateError.value = "";
  managingMember.value = member;
}

async function updateMember(update: MemberUpdate) {
  if (!managingMember.value) return;
  memberUpdateError.value = "";
  try {
    await updateMemberMutation.mutateAsync({
      id: managingMember.value.id,
      update,
    });
    managingMember.value = null;
  } catch (error) {
    memberUpdateError.value = getApiErrorMessage(
      error,
      "Не удалось изменить доступ пользователя.",
    );
  }
}

async function revokeInvitation() {
  if (!revokingInvitation.value) return;
  invitationActionError.value = "";
  try {
    await revokeInvitationMutation.mutateAsync(revokingInvitation.value.id);
    revokingInvitation.value = null;
  } catch (error) {
    invitationActionError.value = getApiErrorMessage(
      error,
      "Не удалось отозвать приглашение.",
    );
  }
}
</script>

<template>
  <div class="min-h-0 flex-1 overflow-y-auto pb-8">
    <div class="mx-auto grid w-full max-w-6xl gap-6">
      <UsersHeader />
      <InviteUsersPanel
        :pending="inviteMutation.isPending.value"
        :reset-key="inviteResetKey"
        @submit="inviteUsers"
      />

      <section class="grid gap-4">
        <UsersTabs
          v-model="tab"
          :member-count="members.length"
          :pending-invitation-count="pendingInvitationCount"
        />
        <UsersToolbar
          v-model:search="search"
          v-model:role="role"
          v-model:status="status"
          :tab="tab"
        />

        <UsersCollectionBody
          v-if="tab === 'members'"
          :pending="membersQuery.isPending.value"
          :error="membersQuery.isError.value"
          :empty="filteredMembers.length === 0"
          empty-title="Пользователи не найдены"
          :empty-description="
            search || role !== 'all' || status !== 'all'
              ? 'Измените параметры поиска или фильтры.'
              : 'Пригласите первого пользователя в рабочее пространство.'
          "
          @retry="membersQuery.refetch()"
        >
          <MembersTable :items="filteredMembers" @manage="openMember" />
        </UsersCollectionBody>

        <UsersCollectionBody
          v-else
          :pending="invitationsQuery.isPending.value"
          :error="invitationsQuery.isError.value"
          :empty="filteredInvitations.length === 0"
          empty-title="Приглашения не найдены"
          :empty-description="
            search || role !== 'all' || status !== 'all'
              ? 'Измените параметры поиска или фильтры.'
              : 'Созданные приглашения появятся здесь.'
          "
          @retry="invitationsQuery.refetch()"
        >
          <InvitationsTable
            :items="filteredInvitations"
            :pending="revokeInvitationMutation.isPending.value"
            @revoke="
              invitationActionError = '';
              revokingInvitation = $event;
            "
          />
        </UsersCollectionBody>
      </section>
    </div>

    <ManageMemberDialog
      :open="managingMember !== null"
      :member="managingMember"
      :pending="updateMemberMutation.isPending.value"
      :error="memberUpdateError"
      :only-active-admin="
        activeAdminCount === 1 &&
        managingMember?.role === 'admin' &&
        managingMember.status === 'active'
      "
      @update:open="
        (open) => {
          if (!open) managingMember = null;
        }
      "
      @save="updateMember"
    />
    <InvitationResultsDialog
      v-model:open="resultsOpen"
      :results="inviteResults"
    />
    <ConfirmAccessActionDialog
      :open="revokingInvitation !== null"
      title="Отозвать приглашение?"
      :description="`Ссылка для ${revokingInvitation?.email ?? ''} перестанет работать.`"
      action-label="Отозвать приглашение"
      :pending="revokeInvitationMutation.isPending.value"
      :error="invitationActionError"
      @update:open="
        (open) => {
          if (!open) {
            revokingInvitation = null;
            invitationActionError = '';
          }
        }
      "
      @confirm="revokeInvitation"
    />
  </div>
</template>
