from typing import Optional

from sqlalchemy import ARRAY, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from geoalchemy2 import Geography

from app.db.base import Base
from pgvector.sqlalchemy import Vector


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_en: Mapped[str] = mapped_column(String(512), nullable=False)
    title_zh: Mapped[str] = mapped_column(String(512), nullable=False)
    content_en: Mapped[str] = mapped_column(Text, nullable=False)
    content_zh: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(128)),
        nullable=False,
        server_default=text("'{}'"),
    )
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="📖")

    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
