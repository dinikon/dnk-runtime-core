from sqlalchemy.ext.asyncio import AsyncSession


class ObjectRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_object(self, object_id: UUID) -> ObjectORM | None:
        return await self._session.get(ObjectORM, object_id)
