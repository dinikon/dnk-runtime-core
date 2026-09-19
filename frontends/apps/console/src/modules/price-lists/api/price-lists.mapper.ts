import type {
  OffersResponse,
  OfferHistoryResponse,
  PartnerOfferState,
  PreviewResult,
  PriceList,
  SyncRun,
} from "../model/types";
import type {
  OffersResponseDto,
  OfferHistoryResponseDto,
  PartnerOfferStateDto,
  PreviewResultDto,
  PriceListDto,
  SyncRunDto,
} from "./price-lists.dto";

export const mapPriceList = (value: PriceListDto): PriceList => ({ ...value });
export const mapPreview = (value: PreviewResultDto): PreviewResult => ({ ...value });
export const mapOffers = (value: OffersResponseDto): OffersResponse => ({
  ...value,
  items: value.items.map((item) => ({ ...item })),
});
export const mapSyncRun = (value: SyncRunDto): SyncRun => ({ ...value });
export const mapOfferState = (value: PartnerOfferStateDto): PartnerOfferState => ({ ...value });
export const mapOfferHistory = (value: OfferHistoryResponseDto): OfferHistoryResponse => ({
  ...value,
  items: value.items.map(mapOfferState),
});
