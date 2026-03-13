from modules.crm.application.contact import ContactDTO
from modules.crm.application.contact.dto import ContactListItemDTO
from src.modules.crm.domain.contact.entity import ContactEntity


def map_contact_to_dto(entity: ContactEntity) -> ContactDTO:
    return ContactDTO(
        id=entity.id.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        first_name=entity.first_name,
        last_name=entity.last_name,
        middle_name=entity.middle_name,
    )


def map_contact_to_list_item_dto(entity: ContactEntity) -> ContactListItemDTO:
    return ContactListItemDTO(
        id=entity.id.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        first_name=entity.first_name,
        last_name=entity.last_name,
        middle_name=entity.middle_name,
    )
