from itertools import zip_longest
import concurrent.futures as futures

from fastapi import status
from httpx import AsyncClient
from tortoise.contrib import test

from main import app
from app.api.api_v1 import settings
from app.api.utils import API_functools
from app.api.api_v1.storage.initial_data import INIT_DATA
from app.api.api_v1.models.pydantic import default_content
from app.api.api_v1.models.tortoise import Person, Comment, Vote

TORTOISE_TEST_DB = getattr(settings, "TORTOISE_TEST_DB", "sqlite://:memory:")
BASE_URL = "http://127.0.0.1:8000"
API_ROOT = "/api/v1/votes/"


class TestPersonAPi(test.TestCase):
    async def insert_votes(
        self,
        votes: list[dict],
        comments: list[dict] = [],
        users: list[dict] = [],
    ) -> None:
        """Test util method: insert some votes data

        Args:
            comments (list[dict]): list of comments, Default [].
            users (list[dict]): list of persons, Default [].
            votes (list[dict]): list of votes , Default [].

        Returns:
            None
        """
        # Insert data
        with futures.ProcessPoolExecutor() as executor:

            for comment, user, vote in zip_longest(comments, users, votes):
                if user:
                    executor.map(
                        await API_functools._insert_default_data(
                            "person", user
                        )
                    )
                if comment:
                    executor.map(
                        await API_functools._insert_default_data(
                            "comment", comment
                        )
                    )
                executor.map(
                    await API_functools._insert_default_data("vote", vote)
                )

    async def test__str__repr__(self):
        user = await Person.create(**INIT_DATA.get("person", [])[0])
        comment = await Comment.create(user=user, content=default_content)
        vote = await Vote.create(user=user, comment=comment)
        expected_repr = "Class({!r})(User={!r}, Comment={!r},...)".format(
            vote.__class__.__name__,
            vote.user.first_name,
            vote.comment.content[:10],
        )
        expected_str = "{!s}(User={!s}, Comment={!s},...)".format(
            vote.__class__.__name__,
            vote.user.first_name,
            vote.comment.content[:10],
        )
        assert vote.__repr__() == expected_repr
        assert vote.__str__() == expected_str

    async def test_get_votes(self):
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT)

        expected = {"detail": "Not Found", "success": False, "votes": []}

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == expected

        # Insert new Comment
        votes_inserted = [*INIT_DATA.get("vote", [])[:4]]
        await self.insert_votes(
            comments=[{**c} for c in INIT_DATA.get("comment", [])[:4]],
            users=[{**p} for p in INIT_DATA.get("person", [])[:4]],
            votes=votes_inserted,
        )

        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT)
        actual = response.json()
        expected = {
            "next": None,
            "previous": None,
            "votes": [
                {
                    "id": pk,
                    "comment_id": vote["comment"],
                    "user_id": vote["user"],
                }
                for pk, vote in enumerate(votes_inserted, start=1)
            ],
        }

        assert response.status_code == status.HTTP_200_OK
        assert expected == actual
