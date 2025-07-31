from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Invitation(Base):
    __tablename__ = 'invitations'
    id = Column(Integer, primary_key=True, index=True)
    family_group_id = Column(Integer, ForeignKey('family_groups.id'), nullable=False)
    email = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending')
    token = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False)

    family_group = relationship('FamilyGroup', back_populates='invitations') 