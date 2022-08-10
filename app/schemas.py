from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, EmailStr, constr


class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    photo: str

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    passwordConfirm: str
    role: str = 'user'
    verified: bool = False


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponse(UserBaseSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class FilteredUserResponse(UserBaseSchema):
    id: uuid.UUID




class PostBaseSchema(BaseModel):
    title: str
    content: str
    category: str
    image: str
    user_id: uuid.UUID | None = None

    class Config:
        orm_mode = True


class CreatePostSchema(PostBaseSchema):             # PostBaseSchema lai inherit gareko cha
    pass


class PostResponse(PostBaseSchema):                 # PostBaseSchema lai inherit gareko cha
    id: uuid.UUID
    user: FilteredUserResponse                      # FilteredUserResponse chai as nested pydantic model jasri use gareko, for sending nested json response
    created_at: datetime
    updated_at: datetime


class UpdatePostSchema(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    image: str | None = None
    user_id: uuid.UUID | None = None

    class Config:
        orm_mode = True


class ListPostResponse(BaseModel):
    status: str
    results: int
    posts: List[PostResponse]                           # PostResponse chai as nested pydantic class jasari use vako cha, for sending nestied json response to the frontend

