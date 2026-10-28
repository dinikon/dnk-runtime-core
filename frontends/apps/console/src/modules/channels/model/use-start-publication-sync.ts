import { publicationApi } from "../api/publication.api";
import { useChannelAction, type ChannelAction } from "./use-channel-action";
import type { StartedPublicationSync } from "./publication.types";
export function useStartPublicationSync(): ChannelAction<
  string,
  StartedPublicationSync
> {
  return useChannelAction((id: string, signal) =>
    publicationApi.start(id, signal),
  );
}
