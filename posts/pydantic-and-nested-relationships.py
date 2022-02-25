import json
import logging
from typing import List

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql.schema import ForeignKey


# Useful for the sequence of queries
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    comments = relationship("Comment", back_populates="user")


class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True)
    comment = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="comments")


class CommentSerializer(BaseModel):
    id: int
    comment: str
    user_id: int

    class Config:
        orm_mode = True


class CommentToStringSerializer(BaseModel):
    comment: str

    class Config:
        orm_mode = True

    def dict(self, **kwargs):
        return super().dict(**kwargs).get("comment", "")


class UserSerializer(BaseModel):
    id: int
    name: str
    comments: List[CommentSerializer]

    class Config:
        orm_mode = True


class UserWithoutIDSerializer(BaseModel):
    name: str
    comments: List[CommentToStringSerializer]

    class Config:
        orm_mode = True


if __name__ == "__main__":

    engine = create_engine("sqlite://", echo=True)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with Session() as session:

        user = User(name="Alice")
        first_comment = Comment(comment="First comment.", user=user)
        second_comment = Comment(comment="Second comment.", user=user)

        session.add(user)
        session.commit()

        logging.info("Run the deserialization")
        bare_result = UserSerializer.from_orm(user).dict()
        tweaked_result = UserWithoutIDSerializer.from_orm(user).dict()

        print(f"bare_result = {json.dumps(bare_result, indent=2)}")
        print(f"tweaked_result = {json.dumps(tweaked_result, indent=2)}")