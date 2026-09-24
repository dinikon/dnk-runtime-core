export const accessQueryKeys = {
  all: ["access"] as const,
  members: () => [...accessQueryKeys.all, "members"] as const,
  invitations: () => [...accessQueryKeys.all, "invitations"] as const,
};
