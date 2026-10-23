import type { CloudStartInput, CloudStatus } from "../model/cloud.types";
import type { CloudStartRequestDto, CloudStatusDto } from "./cloud.dto";

export function mapCloudStatus(dto: CloudStatusDto): CloudStatus {
  return { enabled: dto.enabled, linked: dto.linked };
}

export function mapCloudStart(input: CloudStartInput): CloudStartRequestDto {
  return { purpose: input.purpose, silent: input.silent ?? false };
}
