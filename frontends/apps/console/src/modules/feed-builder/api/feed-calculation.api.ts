import { httpClient } from "@/app/providers/http";
import { feedRequest } from "./feed-request";
import {
  calculationMetadata,
  mapPreview,
  previewPayload,
} from "./feed-calculation.mapper";
import type {
  CalculationParametersDTO,
  CalculationOperationsDTO,
  CalculationPreviewDTO,
} from "./feed-calculation.dto";
import type {
  CalculationMetadata,
  CalculationPreview,
  PreviewRequest,
} from "../model/feed-calculation.types";
const root = "/console/feed-builder";
export const feedCalculationApi = {
  async metadata(signal: AbortSignal): Promise<CalculationMetadata> {
    return feedRequest(async () => {
      const [p, o] = await Promise.all([
        httpClient.get<CalculationParametersDTO>(
          `${root}/calculation-parameters`,
          { signal },
        ),
        httpClient.get<CalculationOperationsDTO>(
          `${root}/calculation-operations`,
          { signal },
        ),
      ]);
      return calculationMetadata(p.data, o.data);
    });
  },
  async preview(
    value: PreviewRequest,
    signal: AbortSignal,
  ): Promise<CalculationPreview> {
    return feedRequest(async () =>
      mapPreview(
        (
          await httpClient.post<CalculationPreviewDTO>(
            `${root}/feeds/${encodeURIComponent(value.feedId)}/calculation-preview`,
            previewPayload(value),
            { signal },
          )
        ).data,
      ),
    );
  },
};
