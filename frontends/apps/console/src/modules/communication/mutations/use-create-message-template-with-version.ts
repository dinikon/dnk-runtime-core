import { useMutation, useQueryClient } from "@tanstack/vue-query";

import { communicationApi } from "@/modules/communication/api";
import type {
  CreateMessageTemplatePayload,
  CreateTemplateVersionPayload,
} from "@/modules/communication/api";
import { communicationQueryKeys } from "@/modules/communication/model/communication.query-keys";

interface CreateMessageTemplateWithVersionPayload {
  template: CreateMessageTemplatePayload;
  version: CreateTemplateVersionPayload;
}

export function useCreateMessageTemplateWithVersionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateMessageTemplateWithVersionPayload) => {
      const template = await communicationApi.createMessageTemplate(
        payload.template,
      );
      const version = await communicationApi.createTemplateVersion(
        template.template_id,
        payload.version,
      );

      await communicationApi.activateTemplateVersion(
        template.template_id,
        version.template_version_id,
      );

      return template;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: communicationQueryKeys.messageTemplates(),
      });
    },
  });
}
