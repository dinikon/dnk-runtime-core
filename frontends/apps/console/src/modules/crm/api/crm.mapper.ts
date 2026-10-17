import { mapContactPoint } from "@/modules/contact-points";
import type { ContactDto, CompanyDto, ContactPointsDto } from "./crm.dto";
import type { Contact, Company, CrmContactPoints } from "../model/crm.types";

export function mapContact(dto: ContactDto): Contact {
  return {
    id: dto.id,
    firstName: dto.first_name,
    lastName: dto.last_name,
    middleName: dto.middle_name,
    displayName: [dto.last_name, dto.first_name, dto.middle_name]
      .filter(Boolean)
      .join(" "),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    createdBy: dto.created_by,
    updatedBy: dto.updated_by,
  };
}

export function mapCompany(dto: CompanyDto): Company {
  return {
    id: dto.id,
    legalName: dto.legal_name,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    createdBy: dto.created_by,
    updatedBy: dto.updated_by,
  };
}

export function mapContactPoints(dto: ContactPointsDto): CrmContactPoints {
  return {
    phones: dto.phones.map(mapContactPoint),
    emails: dto.emails.map(mapContactPoint),
  };
}
