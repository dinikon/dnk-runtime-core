import type {
  OffersResponse,
  PartnerOfferState,
  PreviewResult,
  PriceList,
  SyncRun,
} from "../model/types";

// Decimal values intentionally remain strings at the HTTP boundary.
export type PriceListDto = PriceList;
export type PreviewResultDto = PreviewResult;
export type OffersResponseDto = OffersResponse;
export type SyncRunDto = SyncRun;
export type PartnerOfferStateDto = PartnerOfferState;
