import { httpClient } from "@/app/providers/http";
import { channelRequest } from "./channel.api";
import type {
  ListPublicationsDto,
  GetPublicationDto,
  LatestSyncRunDto,
  StartSyncRunDto,
} from "./publication.dto";
import {
  mapPublicationPage,
  mapPublicationDetails,
  mapSyncRun,
  mapStartedSyncRun,
} from "./publication.mapper";
import type {
  PublicationFilters,
  PublicationPage,
  PublicationDetails,
  PublicationSyncRun,
  StartedPublicationSync,
} from "../model/publication.types";

const root = (id: string): string =>
  "/console/channels/" + encodeURIComponent(id);
export const publicationApi = {
  async list(
    id: string,
    filters: PublicationFilters,
    signal?: AbortSignal,
  ): Promise<PublicationPage> {
    return channelRequest(async () =>
      mapPublicationPage(
        (
          await httpClient.get<ListPublicationsDto>(
            root(id) + "/publications",
            {
              params: {
                search: filters.search,
                offset: filters.offset,
                limit: filters.limit,
                locale: filters.locale || undefined,
              },
              signal,
            },
          )
        ).data,
      ),
    );
  },
  async get(
    id: string,
    publicationId: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<PublicationDetails> {
    return channelRequest(async () =>
      mapPublicationDetails(
        (
          await httpClient.get<GetPublicationDto>(
            root(id) + "/publications/" + encodeURIComponent(publicationId),
            { params: { locale: locale || undefined }, signal },
          )
        ).data,
      ),
    );
  },
  async latest(
    id: string,
    signal?: AbortSignal,
  ): Promise<PublicationSyncRun | null> {
    return channelRequest(async () => {
      const { data } = await httpClient.get<LatestSyncRunDto>(
        root(id) + "/sync-runs/latest",
        { signal },
      );
      return data.sync_run ? mapSyncRun(data.sync_run) : null;
    });
  },
  async start(
    id: string,
    signal?: AbortSignal,
  ): Promise<StartedPublicationSync> {
    return channelRequest(async () =>
      mapStartedSyncRun(
        (
          await httpClient.post<StartSyncRunDto>(
            root(id) + "/sync-runs",
            undefined,
            { signal },
          )
        ).data,
      ),
    );
  },
};
