import { httpClient } from "@/app/providers/http/http-client";
import type { CloudStartInput, CloudStatus } from "../model/cloud.types";
import type { CloudStartResponseDto, CloudStatusDto } from "./cloud.dto";
import { mapCloudStart, mapCloudStatus } from "./cloud.mapper";

export const cloudApi = {
  async status(signal?: AbortSignal): Promise<CloudStatus> {
    const { data } = await httpClient.get<CloudStatusDto>(
      "/auth/cloud/status/",
      { signal },
    );
    return mapCloudStatus(data);
  },
  async start(input: CloudStartInput): Promise<string> {
    const { data } = await httpClient.post<CloudStartResponseDto>(
      "/auth/cloud/start/",
      mapCloudStart(input),
    );
    return data.authorization_url;
  },
};
