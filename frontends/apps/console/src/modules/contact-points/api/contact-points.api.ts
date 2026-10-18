import { httpClient } from "@/app/providers/http";
import type { ContactPointLabel, ContactPointKind } from "../model/types";
interface LabelDto {
  id: string;
  type: ContactPointKind;
  name: string;
  is_active: boolean;
}
const mapLabel = (dto: LabelDto): ContactPointLabel => ({
  id: dto.id,
  type: dto.type,
  name: dto.name,
  isActive: dto.is_active,
});
export const contactPointsApi = {
  async labels(signal?: AbortSignal) {
    const { data } = await httpClient.get<LabelDto[]>(
      "/console/contact-points/labels",
      { signal },
    );
    return data.map(mapLabel);
  },
  async createLabel(type: ContactPointKind, name: string) {
    const { data } = await httpClient.post<LabelDto>(
      "/console/contact-points/labels",
      { type, name },
    );
    return mapLabel(data);
  },
  async updateLabel(
    id: string,
    changes: { name?: string; isActive?: boolean },
  ) {
    const { data } = await httpClient.patch<LabelDto>(
      `/console/contact-points/labels/${id}`,
      {
        ...(changes.name !== undefined ? { name: changes.name } : {}),
        ...(changes.isActive !== undefined
          ? { is_active: changes.isActive }
          : {}),
      },
    );
    return mapLabel(data);
  },
};
