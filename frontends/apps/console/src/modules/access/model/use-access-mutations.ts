import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { accessApi } from "../api/access.api";
import { accessQueryKeys } from "./access.query-keys";
import type { InvitationInput, MemberUpdate } from "./access.types";

export function useInviteMemberMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: InvitationInput) => accessApi.invite(input),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: accessQueryKeys.invitations(),
      }),
  });
}

export function useUpdateMemberMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, update }: { id: string; update: MemberUpdate }) =>
      accessApi.updateMember(id, update),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: accessQueryKeys.members() }),
  });
}

export function useRevokeInvitationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accessApi.revokeInvitation,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: accessQueryKeys.invitations(),
      }),
  });
}
