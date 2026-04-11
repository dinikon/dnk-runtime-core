from enum import Enum


class RelationTypeEnum(str, Enum):
    MANY_TO_ONE = "many_to_one"
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"

    def is_source_owned_fk(self) -> bool:
        return self in {
            RelationTypeEnum.MANY_TO_ONE,
            RelationTypeEnum.ONE_TO_ONE,
        }
