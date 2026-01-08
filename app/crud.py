from sqlalchemy import select
from app.models import Summary

async def get_summary(db, id):
    result = await db.execute(select(Summary).where(Summary.id == id))
    return result.scalar_one_or_none()
