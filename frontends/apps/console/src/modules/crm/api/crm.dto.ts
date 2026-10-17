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
}

export interface CompanyDto {
  id: string;
  legal_name: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

export interface ContactPointsDto {
  phones: ContactPointDto[];
  emails: ContactPointDto[];
}
