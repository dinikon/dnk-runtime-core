import type { ContactPointDto } from "@/modules/contact-points";
export interface ContactDto {
  id: string;
  first_name: string;
  last_name: string | null;
  middle_name: string | null;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  phones: ContactPointDto[];
  emails: ContactPointDto[];
}

export interface CompanyDto {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  phones: ContactPointDto[];
  emails: ContactPointDto[];
}

export interface PageDto<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CrmLinkDto {
  id: string;
  name: string;
}
export interface ContactDetailsDto extends ContactDto {
  companies: CrmLinkDto[];
}
export interface CompanyDetailsDto extends CompanyDto {
  contacts: CrmLinkDto[];
}
