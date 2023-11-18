
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db_config.storage_config import Base, intpk, points, user_fk


class MessageChat(Base):

    __tablename__ = "message_ch"

    id: Mapped[intpk]
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[points]
    # ...
    owner: Mapped[user_fk]
    owner_email: Mapped[str] = mapped_column(String, nullable=False)

    def __str__(self):
        return str(self.id)
