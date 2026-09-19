import type {
  OffersResponse,
  PartnerOfferState,
  PreviewResult,
  PriceList,
  SyncRun,
} from "../model/types";
import type {
  OffersResponseDto,
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
