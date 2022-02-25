# Pydantic and the serialization of nested relationships

```{post} 12, February 2022
```

The objective of this short post is to highlight some features of (de-)serialization with [`pydantic`](https://pydantic-docs.helpmanual.io/):
- filtering capabilities on the spot;
- formatting of the serialization, even for models which include relationships.

The code for this illustration is shown below and will be decomposed in the coming paragraphs.


```{literalinclude} pydantic-and-nested-relationships.py
```


## SQLalchemy models

At first, I am creating two models/tables. The main model `User` is defined by its primary key `id`, a `name` field and the relation to a second model `Comment`. The `Comment` model operates a many-to-one relationship to `User`, a user can "create" several comments.

```{literalinclude} pydantic-and-nested-relationships.py
:lines: 20-34
```

The application of these models is done in the main part of the code where a single instance of `User` is created, followed by two comments.

```{literalinclude} pydantic-and-nested-relationships.py
:lines: 79-83
:emphasize-lines: 3-5
```

## Pydantic for (de-)serialization

After the SQLalchemy models comes two sets of serializers:
- the first set, `CommentSerializer` and `UserSerializer`, covering all the parameters that the SQLalchemy models offer (including the primary keys which are settled upon commit). The `orm_mode=True` allows for passing the instance of the model directly into the serializer. As you can see, there is no tweaking;
```{literalinclude} pydantic-and-nested-relationships.py
:lines: 37-45, 56-62
```
- the second set, `CommentToStringSerializer` and `UserWithoutIDSerializer`, illustrates the possibilities offered by `pydantic`, namely filtering out unnecessary parameters (here `id` and `user_id`) and transforming the result of the `dict` method.
```{literalinclude} pydantic-and-nested-relationships.py
:lines: 46-55, 65-70
```
## Deserialization of queries results

With those sets of models and serializers, I can now illustrate on an example the handy features of the deserialization offered by `pydantic`. 

I am using a simple SQLite in-memory database. As mentioned before, after creating the tables, those are fed with a single user and two comments for them. Once committed, both the user and the comments acquire their respective `id`.
```{literalinclude} pydantic-and-nested-relationships.py
:lines: 73-86
```

The first serialization
```{literalinclude} pydantic-and-nested-relationships.py
:lines: 89-93
:emphasize-lines: 1,4
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
```{literalinclude} pydantic-and-nested-relationships.py
:lines: 89-93
:emphasize-lines: 2,5
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

```{literalinclude} pydantic-and-nested-relationships.py
:lines: 89-90
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