from datetime import date
from typing import Optional, Type, TypeVar

from ..models.types import Gender
from ...utils import API_functools
from pydantic import BaseModel, validator, EmailStr, HttpUrl

avatar = "https://robohash.org/autdoloremaccusamus.png?size=150x150&set=set1"
default_content = """Lorem ipsum dolor sit amet consectetur adipisicing elit.
Consequuntur ratione omnis alias magnam?"""

PU = TypeVar("PU", bound="PartialUser")


class PartialUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    avatar: Optional[HttpUrl]
    company: Optional[str]
    job: Optional[str]

    @classmethod
    @validator("last_name", "first_name", "job", "company")
    def between_3_and_50_characters(cls: Type[PU], value: str, **kwargs) -> str:
        """Validate str attributes that must contains minimum 3 characters\
            and maximum 50 characters\n

        Args:\n
            value (str): attribute to validate

        Raises:
            ValueError: if constraint not respected

        Returns:
            str: validate attribute
        """
        str_to_validate = API_functools.strip_spaces(value.title())
        if not (3 <= len(str_to_validate) <= 50):
            raise ValueError(
                f"{kwargs['field'].name} must contain between 3 and 50 \
                    characters."
            )
        return value

    class Config:
        schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "DOE",
                "email": "john.doe@eliam-lotonga.fr",
                "avatar": avatar,
                "job": "Compensation Analyst",
                "company": "Edgetag",
            }
        }


U = TypeVar("U", bound="User")


class User(PartialUser):
    is_admin: Optional[bool] = False
    gender: Gender
    date_of_birth: date
    country_of_birth: str

    @validator("country_of_birth")
    def between_3_and_50_characters(cls: Type[U], value: str) -> Optional[str]:
        return super().between_3_and_50_characters(value)

    class Config:
        schema_extra = {
            "example": {
                "is_admin": False,
                "first_name": "John",
                "last_name": "DOE",
                "email": "john.doe@eliam-lotonga.fr",
                "gender": "Male",
                "avatar": avatar,
                "job": "Compensation Analyst",
                "company": "Edgetag",
                "date_of_birth": "1970-01-01",
                "country_of_birth": "No where",
            }
        }


PC = TypeVar("PC", bound="PartialComment")


class PartialComment(BaseModel):
    content: str

    @classmethod
    @validator("country_of_birth")
    def at_least_1_character(cls: Type[PC], value: str, **kwargs) -> Optional[str]:
        """Validate content that must contains minimum 1 character\

        Args:\n
            value (str): content to validate

        Raises:
            ValueError: if constraint not respected

        Returns:
            str: valid content
        """
        str_to_validate = API_functools.strip_spaces(value.title())
        if len(str_to_validate) <= 1:
            raise ValueError(
                f"{kwargs['field'].name} must contain at least 1\
                    character."
            )
        return value

    class Config:
        schema_extra = {
            "example": {
                "content": default_content,
            }
        }


C = TypeVar("C", bound="Comment")


class Comment(PartialComment):
    user: int = 0
    top_parent: int = 0
    parent: int = 0

    class Config:
        schema_extra = {
            "example": {
                "user": 1,
                "content": default_content,
            }
        }


class Vote(BaseModel):
    comment: int
    user: int

    class Config:
        schema_extra = {
            "example": {
                "user": 1,
                "comment": 1,
            }
        }
