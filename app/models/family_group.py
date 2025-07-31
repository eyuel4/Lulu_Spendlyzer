from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.models.base import Base

class FamilyGroup(Base):
    __tablename__ = 'family_groups'
    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey('users.id', use_alter=True), nullable=False)
    family_name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

    users = relationship('User', back_populates='family_group', foreign_keys='User.family_group_id')
    invitations = relationship('Invitation', back_populates='family_group') 