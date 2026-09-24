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
  MemberStatus,
  Role,
} from "../model/access.types";
import ConfirmAccessActionDialog from "../ui/common/ConfirmAccessActionDialog.vue";
import UsersCollectionBody from "../ui/common/UsersCollectionBody.vue";
import UsersTabs from "../ui/common/UsersTabs.vue";
import UsersToolbar from "../ui/common/UsersToolbar.vue";
import InvitationResultsDialog from "../ui/invitations/InvitationResultsDialog.vue";
import InvitationsTable from "../ui/invitations/InvitationsTable.vue";
import InviteUsersPanel from "../ui/invitations/InviteUsersPanel.vue";
import ChangeMemberRoleDialog from "../ui/members/ChangeMemberRoleDialog.vue";
import ChangeMemberStatusDialog from "../ui/members/ChangeMemberStatusDialog.vue";
import MembersTable from "../ui/members/MembersTable.vue";
import UsersHeader from "../ui/page/UsersHeader.vue";

const membersQuery = useMembersQuery();
const invitationsQuery = useInvitationsQuery();
const inviteMutation = useInviteMemberMutation();
const updateMemberRoleMutation = useUpdateMemberMutation();
const updateMemberStatusMutation = useUpdateMemberMutation();
const revokeInvitationMutation = useRevokeInvitationMutation();
const { role, search, status, tab } = useUsersPageState();

const roleMember = ref<Member | null>(null);
const roleUpdateError = ref("");
const statusMember = ref<Member | null>(null);
const statusUpdateError = ref("");
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

function isOnlyActiveAdmin(member: Member | null) {
  return (
    activeAdminCount.value === 1 &&
    member?.role === "admin" &&
    member.status === "active"
  );
}

function openRoleDialog(member: Member) {
  roleUpdateError.value = "";
  roleMember.value = member;
}

function openStatusDialog(member: Member) {
  statusUpdateError.value = "";
  statusMember.value = member;
}

async function updateMemberRole(nextRole: Role) {
  const member = roleMember.value;
  if (!member) return;
  roleUpdateError.value = "";
  try {
    await updateMemberRoleMutation.mutateAsync({
      id: member.id,
      update: { role: nextRole },
    });
    roleMember.value = null;
  } catch (error) {
    roleUpdateError.value = getApiErrorMessage(
      error,
      "Не удалось изменить роль пользователя.",
    );
  }
}

async function updateMemberStatus(nextStatus: MemberStatus) {
  const member = statusMember.value;
  if (!member) return;
  statusUpdateError.value = "";
  try {
    await updateMemberStatusMutation.mutateAsync({
      id: member.id,
      update: { status: nextStatus },
    });
    statusMember.value = null;
  } catch (error) {
    statusUpdateError.value = getApiErrorMessage(
      error,
      nextStatus === "revoked"
        ? "Не удалось уволить пользователя."
        : "Не удалось восстановить пользователя.",
    );
  }
}

async function revokeInvitation() {
  const invitation = revokingInvitation.value;
  if (!invitation) return;
  invitationActionError.value = "";
  try {
    await revokeInvitationMutation.mutateAsync(invitation.id);
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
          <MembersTable
            :items="filteredMembers"
            @change-role="openRoleDialog"
            @change-status="openStatusDialog"
          />
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

    <ChangeMemberRoleDialog
      :open="roleMember !== null"
      :member="roleMember"
      :pending="updateMemberRoleMutation.isPending.value"
      :error="roleUpdateError"
      :only-active-admin="isOnlyActiveAdmin(roleMember)"
      @update:open="
        (open) => {
          if (!open) {
            roleMember = null;
            roleUpdateError = '';
          }
        }
      "
      @save="updateMemberRole"
    />
    <ChangeMemberStatusDialog
      :open="statusMember !== null"
      :member="statusMember"
      :pending="updateMemberStatusMutation.isPending.value"
      :error="statusUpdateError"
      :only-active-admin="isOnlyActiveAdmin(statusMember)"
      @update:open="
        (open) => {
          if (!open) {
            statusMember = null;
            statusUpdateError = '';
          }
        }
      "
      @confirm="updateMemberStatus"
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
