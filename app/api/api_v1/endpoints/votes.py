from functools import cache
from typing import Optional, Dict, List, Any

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, status, Request, Response

from app.api.utils import API_functools
from app.api.api_v1.models.tortoise import Vote


router = APIRouter()


@cache
@router.get("/", status_code=status.HTTP_200_OK)
async def votes(
    request: Request,
    res: Response,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:

    """Get all votes or some of them using 'offset' and 'limit'\n

    Args:\n
        limit (int, optional): max number of returned votes. \
        Defaults to 100.\n
        offset (int, optional): first comment to return (use with limit). \
        Defaults to 1.\n
        sort (str, optional): the order of the result. \
        attribute:(asc {ascending} or desc {descending}). \
        Defaults to "id:asc".\n
    Returns:\n
        Optional[List[Dict[str, Any]]]: list of votes found or \
        Dict with error\n
    """
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
    nb_votes = await Vote.all().count()

    votes = jsonable_encoder(
        await Vote.all()
        .limit(limit)
        .offset(offset)
        .order_by(order_by)
        .values(*API_functools.get_attributes(Vote))
    )

    if len(votes) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return API_functools.manage_next_previous_page(
        request, votes, nb_votes, limit, offset, data_type="votes"
    )
