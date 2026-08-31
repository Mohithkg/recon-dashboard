from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Future tables will reference this via user_id
    # orders = relationship("Order", back_populates="user")
    # payments = relationship("Payment", back_populates="user")
    # discrepancies = relationship("Discrepancy", back_populates="user")


# Foreign key pattern for future tables — copy this into Order, Payment, Discrepancy:
# user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
# user = relationship("User", back_populates="<name>")
