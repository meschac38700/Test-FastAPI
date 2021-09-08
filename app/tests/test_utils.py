import pytest
from fastapi import Request
from tortoise.contrib import test
from fastapi.encoders import jsonable_encoder

from app.api.utils import API_functools
from app.api.api_v1.models.pydantic import avatar
from app.api.api_v1.storage.initial_data import INIT_DATA
from app.api.api_v1.models.tortoise import Person, Comment, Vote


class TestUtils(test.TestCase):
    async def test_tortoise_to_dict(self):
        actual = API_functools.tortoise_to_dict(
            await Person(**INIT_DATA.get("person", [])[0])
        )
        actual["date_of_birth"] = jsonable_encoder(actual["date_of_birth"])
        assert actual == {
            "avatar": avatar,
            "company": "Edgetag",
            "country_of_birth": "Egypt",
            "date_of_birth": "1978-04-15",
            "email": "shandes0@un.org",
            "first_name": "Shalom",
            "gender": "Male",
            "id": None,
            "is_admin": True,
            "job": "Compensation Analyst",
            "last_name": "Handes",
        }

    def test_strip_spaces(self):
        s = API_functools.strip_spaces("       Hello         World       ")
        assert s == "Hello World"

    def test_get_or_default(self):
        list_object = (
            {"name": "John Doe"},
            {"name": "Bob Doe"},
            {"name": "Alice Doe"},
        )
        for index, obj in enumerate(list_object):
            assert API_functools.get_or_default(list_object, index, None) == obj
        assert API_functools.get_or_default(list_object, len(list_object), None) is None

    async def test_instance_of(self):
        obj = await Person.create(**INIT_DATA.get("person", [])[0])
        elements = {
            "Hello World": str,
            1: int,
            obj: Person,
            (1, 2, 3, 4): tuple,
        }
        for el, instance in elements.items():
            assert API_functools.instance_of(el, instance) is True
        assert API_functools.instance_of("Hello", int) is False

    def test_get_attributes(self):
        # Test get_attribute with kwargs
        user_attributes = (
            "id",
            "is_admin",
            "name",
            "email",
            "gender",
            "avatar",
            "job",
            "company",
            "date_of_birth",
            "country_of_birth",
            "full_name",
        )
        assert (
            API_functools.get_attributes(
                Person,
                replace={"first_name": "name"},
                add=("full_name",),
                exclude=("last_name",),
            )
            == user_attributes
        )

    def test_valid_order(self):
        # valid order must consist of an attribute of the Person class
        # and the word "asc" or "desc"
        orders = [
            ("first_name", None),
            ("notattributte:asc", None),
            ("id:notvalidkeyword", None),
            ("first_name:asc", "first_name"),
            ("first_name:desc", "-first_name"),
        ]
        for order in orders:
            assert API_functools.valid_order(Person, order[0]) == order[1]

    def test_is_attribute_of(self):
        for attr in API_functools.get_attributes(Person):
            assert API_functools.is_attribute_of(attr, Person) is True
        assert API_functools.is_attribute_of("invalid", Person) is False

    def test_manage_next_previous_page(self):
        scope = {"type": "http", "path": "/", "method": "GET"}
        request = Request(scope)
        scenes = [
            {
                "data": (0, 5, 0),  # nb_total_data, limit, offset
                "expected": {
                    "next": None,
                    "previous": None,
                    "success": False,
                    "users": [],
                },
            },
            {
                "data": (15, 5, 5),
                "expected": {
                    "next": "/?limit=5&offset=10",
                    "previous": "/?limit=5&offset=0",
                    "success": False,
                    "users": [],
                },
            },
            {
                "data": (10, 5, 0),
                "expected": {
                    "next": "/?limit=5&offset=5",
                    "previous": None,
                    "success": False,
                    "users": [],
                },
            },
            {
                "data": (10, 5, 5),
                "expected": {
                    "next": None,
                    "previous": "/?limit=5&offset=0",
                    "success": False,
                    "users": [],
                },
            },
        ]
        for scene in scenes:
            # scene 1 next=None, previous=None
            actual = API_functools.manage_next_previous_page(
                request, [], *scene["data"], data_type="users"
            )
            assert actual == scene["expected"]

    async def test_insert_default_data(self):
        nb_users_inserted = 4
        await API_functools.insert_default_data(
            table="person",
            data=[*INIT_DATA.get("person", [])[:nb_users_inserted]],
        )
        with pytest.raises(ValueError):
            await API_functools.insert_default_data(
                table="person",
                data=None,
            )
        assert await Person.all().count() == nb_users_inserted

    async def test__insert_default_data(self):
        # Insert a Person
        user_to_create = INIT_DATA.get("person", [])[0]
        user_created = await API_functools._insert_default_data("person", user_to_create)
        assert API_functools.instance_of(user_created, Person) is True

        # Insert a Comment
        comment_to_create = {
            **INIT_DATA.get("comment", [])[0],
            "user": user_created.id,
        }
        comment_created = await API_functools._insert_default_data(
            "comment", comment_to_create
        )
        assert API_functools.instance_of(comment_created, Comment) is True

        # Insert a Vote
        vote_to_create = {
            "user": user_created.id,
            "comment": comment_created.id,
        }
        vote_created = await API_functools._insert_default_data("vote", vote_to_create)
        assert API_functools.instance_of(vote_created, Vote) is True
