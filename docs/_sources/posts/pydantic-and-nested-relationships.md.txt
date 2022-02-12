# Pydantic and the serialization of nested relationships

```{post} 12, February 2022
```

The objective of this short post is to highlight some features of (de-)serialization with [`pydantic`](https://pydantic-docs.helpmanual.io/):
- filtering capabilities on the spot;
- formatting of the serialization, even for models which include relationships.

The code for this illustration is shown below and will be decomposed in the coming paragraphs.

```python
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
```


## SQLalchemy models

At first, I am creating two models/tables. The main model `User` is defined by its primary key `id`, a `name` field and the relation to a second model `Comment`. The `Comment` model operates a many-to-one relationship to `User`, a user can "create" several comments.

```python
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
```

The application of these models is done in the main part of the code where a single instance of `User` is created, followed by two comments.

```python
user = User(name="Alice")
first_comment = Comment(comment="First comment.", user=user)
second_comment = Comment(comment="Second comment.", user=user)
```

## Pydantic for (de-)serialization

After the SQLalchemy models comes two sets of serializers:
- the first set, `CommentSerializer` and `UserSerializer`, covering all the parameters that the SQLalchemy models offer (including the primary keys which are settled upon commit). The `orm_mode=True` allows for passing the instance of the model directly into the serializer. As you can see, there is no tweaking;
- the second set, `CommentToStringSerializer` and `UserWithoutIDSerializer`, illustrates the possibilities offered by `pydantic`, namely filtering out unnecessary parameters (here `id` and `user_id`) and transforming the result of the `dict` method.

```python
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
```

## Deserialization of queries results

With those sets of models and serializers, I can now illustrate on an example the handy features of the deserialization offered by `pydantic`. 

I am using a simple SQLite in-memory database. As mentioned before, after creating the tables, those are fed with a single user and two comments for them. Once committed, both the user and the comments acquire their respective `id`.

```python
engine = create_engine("sqlite://")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

with Session() as session:

    user = User(name="Alice")
    first_comment = Comment(comment="First comment.", user=user)
    second_comment = Comment(comment="Second comment.", user=user)

    session.add(user)
    session.commit()
```

The first serialization
```python
bare_result = UserSerializer.from_orm(user)
# ...
print(f"bare_result = {bare_result.json(indent=2)}")
```
indeed reads as
```
bare_result = {
  "id": 1,
  "name": "Alice",
  "comments": [
    {
      "id": 1,
      "comment": "First comment.",
      "user_id": 1
    },
    {
      "id": 2,
      "comment": "Second comment.",
      "user_id": 1
    }
  ]
}
```

The second serialization
```python
tweaked_result = UserWithoutIDSerializer.from_orm(user)
# ...
print(f"tweaked_result = {tweaked_result.json(indent=2)}")
```
highlights the capabilities of `pydantic` as the result reads as
```
tweaked_result = {
  "name": "Alice",
  "comments": [
    "First comment.",
    "Second comment."
  ]
}
```

As expected, the `id` disappeared from the response `tweaked_result` while the list of comments only contains the strings. Note that the parsing has been done on the same instance `user` as fed to `bare_result`. 

```python
bare_result = UserSerializer.from_orm(user)
tweaked_result = UserWithoutIDSerializer.from_orm(user)
```

`pydantic` is responsible for the formatting of the response.

> For the users of [FastAPI](https://fastapi.tiangolo.com/), if your endpoint returns `user`, you can pass `UserWithoutIDSerializer` as the `response_model` to get a JSON response similar to `tweaked_result`.

## Notes on the queries

While reading the code, you will realize that there is no explicit query of the models. The query only happens "implicitly" during the deserialization of the `User`, as shown by the extract below. 

```
2022-02-12 10:03:19,400 - sqlalchemy.engine.Engine - INFO - COMMIT
2022-02-12 10:03:19,400 - root - INFO - Run the deserialization
[...]
2022-02-12 10:03:19,402 - sqlalchemy.engine.Engine - INFO - SELECT user.id AS user_id, user.name AS user_name 
FROM user 
WHERE user.id = ?
[...]
2022-02-12 10:03:19,405 - sqlalchemy.engine.Engine - INFO - SELECT comment.id AS comment_id, comment.comment AS comment_comment, comment.user_id AS comment_user_id 
FROM comment 
WHERE ? = comment.user_id
```

In terms of performance, this is far from optimal since, as you can see, there are several queries in sequence to get both the user and the related comments. It would make more sense to load eagerly the comments with the user like
```python
from sqlalchemy.orm import joinedload
# ...
query = select(User).options(joinedload(User.comments))
user, = session.execute(query).first()
```