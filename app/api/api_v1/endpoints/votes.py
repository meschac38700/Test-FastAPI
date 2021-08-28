from functools import cache
from typing import Optional, Dict, List, Any

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, status, Request, Response

from app.api.utils import API_functools
from app.api.api_v1.models.pydantic import Vote as VoteBaseModel
from app.api.api_v1.models.tortoise import Vote, Comment, Person


router = APIRouter()


async def filter_votes(
    req: Request,
    res: Response,
    max_votes: int,
    filters: Optional[dict] = None,
    offset: Optional[int] = 20,
    limit: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:
    response = {
        "success": False,
        "votes": [],
    }
    order_by = API_functools.valid_order(Vote, sort)

    if order_by is None:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {
            **response,
            "detail": "Invalid sort parameters. it must match \
            attribute:order. ex: id:asc or id:desc",
        }

    if offset < 0 or limit < 1:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {
            **response,
            "detail": "Invalid values: offset(>=0) or limit(>0)",
        }

    votes = jsonable_encoder(
        await (Vote.all() if filters is None else Vote.filter(**filters))
        .limit(limit)
        .offset(offset)
        .order_by(order_by)
        .values(*API_functools.get_attributes(Vote))
    )
    if len(votes) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return API_functools.manage_next_previous_page(
        req, votes, max_votes, limit, offset, data_type="votes"
    )


@cache
@router.get("/", status_code=status.HTTP_200_OK)
async def votes(
    req: Request,
    res: Response,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:

    """Get all votes or some of them using 'offset' and 'limit'\n

    Args:\n
        limit (int, optional): max number of returned votes. \
        Defaults to 100.\n
        offset (int, optional): first vote to return (use with limit). \
        Defaults to 1.\n
        sort (str, optional): the order of the result. \
        attribute:(asc {ascending} or desc {descending}). \
        Defaults to "id:asc".\n
    Returns:\n
        Optional[List[Dict[str, Any]]]: list of votes found or \
        Dict with error\n
    """
    nb_votes = await Vote.all().count()

    return await filter_votes(
        req, res, nb_votes, offset=offset, limit=limit, sort=sort
    )


@cache
@router.get("/comment/{comment_ID}", status_code=status.HTTP_200_OK)
async def votes_by_comment(
    req: Request,
    res: Response,
    comment_ID: int,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:

    """Get all votes of comment or some of them using 'offset' and 'limit'\n

    Args:\n
        user_ID (int): user ID
        limit (int, optional): max number of votes to return. \
        Defaults to 100.\n
        offset (int, optional): first vote to return (use with limit). \
        Defaults to 1.\n
        sort (str, optional): the order of the result. \
        attribute:(asc {ascending} or desc {descending}). \
        Defaults to "id:asc".\n
    Returns:\n
        Optional[List[Dict[str, Any]]]: list of votes found or \
        Dict with error\n
    """
    comment = await Comment.filter(pk=comment_ID)

    if len(comment) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {
            "success": False,
            "votes": [],
            "detail": f"Comment {comment_ID} doesn't exist",
        }

    return await filter_votes(
        req,
        res,
        len(comment),
        filters={"comment_id": comment_ID},
        offset=offset,
        limit=limit,
        sort=sort,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_vote(res: Response, vote: VoteBaseModel) -> Dict[str, Any]:
    """Create new vote\n

    Args:\n
        vote (VoteBaseModel): vote to create\n

    Returns:\n
        Dict[str, Any]: vote created\n
    """
    response = {
        "success": True,
        "vote": {},
        "detail": "Vote successfully created",
    }
    vote_owner = API_functools.get_or_default(
        await Person.filter(pk=vote.user), 0, None
    )
    if vote_owner is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["success"] = False
        response["detail"] = "Vote owner doesn't exist"
        return response

    vote_comment = API_functools.get_or_default(
        await Comment.filter(pk=vote.comment), 0, None
    )

    if vote_comment is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["success"] = False
        response["detail"] = "Vote comment doesn't exist"
        return response

    response["vote"] = API_functools.tortoise_to_dict(
        await Vote.create(comment=vote_comment, user=vote_owner)
    )

    return jsonable_encoder(response)
