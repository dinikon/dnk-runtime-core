import { mapContactPoint } from "@/modules/contact-points";
import type { CompanyDto, ContactDto, PageDto } from "./crm.dto";
import type { Company, Contact, Page } from "../model/crm.types";

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
    phones: dto.phones.map(mapContactPoint),
    emails: dto.emails.map(mapContactPoint),
  };
}

export function mapCompany(dto: CompanyDto): Company {
  return {
    id: dto.id,
    name: dto.name,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    createdBy: dto.created_by,
    updatedBy: dto.updated_by,
    phones: dto.phones.map(mapContactPoint),
    emails: dto.emails.map(mapContactPoint),
  };
}

export function mapPage<TDto, TModel>(
  dto: PageDto<TDto>,
  mapper: (item: TDto) => TModel,
): Page<TModel> {
  return {
    items: dto.items.map(mapper),
    total: dto.total,
    limit: dto.limit,
    offset: dto.offset,
  };
}
