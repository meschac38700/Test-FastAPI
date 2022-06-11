import pytest

from pydantic import BaseConfig, Field
from pydantic.fields import ModelField
from tortoise.contrib import test

from app.api.api_v1.models.pydantic import PartialUser


class TestPydantic(test.TestCase):
    def test_between_3_and_50_characters(self):
        f = Field(..., min_length=3, max_length=50)
        field = ModelField(
            name="name",
            type_=str,
            class_validators={},
            field_info=f,
            model_config=BaseConfig,
        )
        long_text = "Lorem Ipsum is simply dummy text of\
                the printing and typesetting industry. "
        with pytest.raises(ValueError):

            PartialUser.between_3_and_50_characters("He", field=field)

        with pytest.raises(ValueError):
            PartialUser.between_3_and_50_characters(
                long_text,
                field=field,
            )
        assert PartialUser.between_3_and_50_characters("Hello") == "Hello"
