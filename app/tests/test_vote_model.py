import json

from typing import Dict, List, Any
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

ObjectDict = Dict[str, Any]

TORTOISE_TEST_DB = getattr(settings, "TORTOISE_TEST_DB", "sqlite://:memory:")
BASE_URL = "http://127.0.0.1:8000"
API_ROOT = "/api/v1/votes/"


class TestVoteAPi(test.TestCase):
    async def insert_votes(
        self,
        votes: List[ObjectDict],
        comments: List[ObjectDict] = [],
        users: List[ObjectDict] = [],
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
                    executor.map(await API_functools._insert_default_data("person", user))
                if comment:
                    executor.map(
                        await API_functools._insert_default_data("comment", comment)
                    )
                executor.map(await API_functools._insert_default_data("vote", vote))

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

    def test_vote_attributes(self):
        expected_attrs = (
            "id",
            "comment_id",
            "user_id",
        )
        actual_attrs: tuple[str] = API_functools.get_attributes(Vote)
        for attr in expected_attrs:
            assert attr in actual_attrs
        assert len(expected_attrs) == len(actual_attrs)

    async def test_get_votes(self):
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT)

        expected: ObjectDict = {"detail": "Not Found", "success": False, "votes": []}

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
            "success": True,
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

    async def test_get_votes_with_limit_offset(self):
        limit = 4
        offset = 0
        comments = [*INIT_DATA.get("comment", [])[: limit + 4]]
        users = INIT_DATA.get("person", [])[: limit + 4]
        votes = INIT_DATA.get("vote", [])[: limit + 4]

        # insert data
        await self.insert_votes(comments=comments, users=users, votes=votes)

        # Scene 1 get first data, previous=Null
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"limit": limit, "offset": offset})
        actual = response.json()
        expected = {
            "next": f"{API_ROOT}?limit={limit}&offset={limit}",
            "previous": None,
            "success": True,
            "votes": [
                {
                    "id": pk,
                    "comment_id": vote["comment"],
                    "user_id": vote["user"],
                }
                for pk, vote in enumerate(votes[:limit], start=1)
            ],
        }

        assert response.status_code == status.HTTP_200_OK
        assert actual == expected

        # Scene 2 get last data, next=Null
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"limit": limit, "offset": limit})
        actual = response.json()

        expected = {
            "success": True,
            "next": None,
            "previous": f"{API_ROOT}?limit={limit}&offset={offset}",
            "votes": [
                {
                    "id": pk + limit,
                    "comment_id": vote["comment"],
                    "user_id": vote["user"],
                }
                for pk, vote in enumerate(votes[limit:], start=1)
            ],
        }

        assert response.status_code == status.HTTP_200_OK
        assert actual == expected

        limit = 0
        offset = -1
        # Test bad limit and offset values
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"limit": limit, "offset": limit})

        expected: ObjectDict = {
            "success": False,
            "votes": [],
            "detail": "Invalid values: offset(>=0) or limit(>0)",
        }
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected

    async def test_votes_sorted_by_attribute(self):
        # sort by user id ascending order
        commentID_asc = "comment_id:asc"
        # sort by date added descending order
        userID_desc = "user_id:desc"
        data_nbr = 4

        comments: List[ObjectDict] = [*INIT_DATA.get("comment", [])[:data_nbr]]
        users: List[ObjectDict] = INIT_DATA.get("person", [])[:data_nbr]
        votes: List[ObjectDict] = INIT_DATA.get("vote", [])[:data_nbr]

        await self.insert_votes(comments=comments, users=users, votes=votes)

        # Test order by content ASC
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"sort": commentID_asc})

        actual = response.json()
        votes = sorted(
            [
                {
                    "comment_id": v["comment"],
                    "user_id": v["user"],
                    "id": pk,
                }
                for pk, v in enumerate(votes, start=1)
            ],
            key=lambda order: order[commentID_asc.split(":")[0]],
        )
        expected: ObjectDict = {
            "next": None,
            "previous": None,
            "success": True,
            "votes": votes,
        }

        assert response.status_code == status.HTTP_200_OK
        assert actual == expected

        # Test order by added DESC
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"sort": userID_desc})

        actual = response.json()
        votes = sorted(
            votes,
            key=lambda u: u[userID_desc.split(":")[0]],
            reverse=True,
        )
        expected = {
            "next": None,
            "previous": None,
            "success": True,
            "votes": votes,
        }

        assert response.status_code == status.HTTP_200_OK
        assert actual == expected

        # Test bad order by
        order_by = "undefined:asc"
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(API_ROOT, params={"sort": order_by})
        detail = "Invalid sort parameters. it must match \
            attribute:order. ex: id:asc or id:desc"
        expected: ObjectDict = {
            "success": False,
            "votes": [],
            "detail": detail,
        }
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected

    async def test_votes_by_comment(self):
        # sort by user id ascending order
        comment_ID = 1
        data_nbr = 20
        comments = [*INIT_DATA.get("comment", [])[:data_nbr]]
        users = INIT_DATA.get("person", [])[:data_nbr]
        votes = INIT_DATA.get("vote", [])[:data_nbr]

        await self.insert_votes(comments=comments, users=users, votes=votes)

        # comment doesn't exist
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_ROOT}comment/{data_nbr+1}")

            actual: ObjectDict = response.json()

            expected: ObjectDict = {
                "success": False,
                "votes": [],
                "detail": f"Comment {data_nbr+1} doesn't exist",
            }

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert actual == expected

        # Success
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_ROOT}comment/{comment_ID}")

            actual = response.json()
            votes = [
                {
                    "id": pk,
                    "comment_id": v["comment"],
                    "user_id": v["user"],
                }
                for pk, v in enumerate(votes, start=1)
                if v["comment"] == comment_ID
            ]
            expected = {
                "next": None,
                "previous": None,
                "success": True,
                "votes": votes,
            }

            assert response.status_code == status.HTTP_200_OK
            assert actual == expected

    async def test_votes_by_user(self):
        # sort by user id ascending order
        user_ID = 1
        data_nbr = 20
        comments: List[ObjectDict] = [*INIT_DATA.get("comment", [])[:data_nbr]]
        users: List[ObjectDict] = INIT_DATA.get("person", [])[:data_nbr]
        votes: List[ObjectDict] = INIT_DATA.get("vote", [])[:data_nbr]

        await self.insert_votes(comments=comments, users=users, votes=votes)

        # comment doesn't exist
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_ROOT}user/{data_nbr+1}")

            actual = response.json()
            expected: ObjectDict = {
                "success": False,
                "votes": [],
                "detail": f"User {data_nbr+1} doesn't exist",
            }

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert actual == expected

        # Success
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_ROOT}user/{user_ID}")

            actual = response.json()
            votes = [
                {
                    "id": pk,
                    "comment_id": v["comment"],
                    "user_id": v["user"],
                }
                for pk, v in enumerate(votes, start=1)
                if v["user"] == user_ID
            ]
            expected = {
                "next": None,
                "previous": None,
                "success": True,
                "votes": votes,
            }

            assert response.status_code == status.HTTP_200_OK
            assert actual == expected

    async def test_create_remove_vote(self):

        vote = INIT_DATA.get("vote", [])[0]

        # User doesn't exist
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(API_ROOT, data=json.dumps(vote))
            expected: ObjectDict = {
                "success": False,
                "vote": {},
                "detail": "Vote owner doesn't exist",
            }
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == expected

        user = await Person.create(**INIT_DATA.get("person", [])[0])
        # Comment doesn't exist
        expected["detail"] = "Vote comment doesn't exist"

        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(API_ROOT, data=json.dumps(vote))
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == expected

        await Comment.create(**{**INIT_DATA.get("comment", [])[0], "user": user})

        # Add vote
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(API_ROOT, data=json.dumps(vote))

        expected = {
            "success": True,
            "vote": {
                "id": 1,
                "comment_id": vote["comment"],
                "user_id": vote["user"],
            },
            "votes": 1,
            "detail": "Vote successfully created",
        }
        # Remove vote
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(API_ROOT, data=json.dumps(vote))

            expected["votes"] = 0

            assert response.status_code == status.HTTP_202_ACCEPTED
            assert response.json() == expected

    async def test_delete_vote(self):
        # vote doesn't exist
        vote_ID = 1
        vote_to_delete = INIT_DATA.get("vote", [])[0]
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.delete(f"{API_ROOT}{vote_ID}")
            expected: ObjectDict = {
                "success": False,
                "vote": {},
                "detail": f"Vote with ID {vote_ID} doesn't exist",
            }
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == expected

        # Insert new vote
        await self.insert_votes(
            comments=[INIT_DATA.get("comment", [])[0]],
            users=[INIT_DATA.get("person", [])[0]],
            votes=[vote_to_delete],
        )

        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.delete(f"{API_ROOT}{vote_ID}")

        actual = response.json()
        expected = {
            "success": True,
            "vote": {
                "id": vote_ID,
                "comment_id": vote_to_delete["comment"],
                "user_id": vote_to_delete["user"],
            },
            "detail": f"Vote {vote_ID} deleted successfully ⭐",
        }
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert actual == expected
        assert await Vote.filter(id=vote_ID).first() is None
