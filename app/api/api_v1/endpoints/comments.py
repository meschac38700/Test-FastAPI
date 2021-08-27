from functools import cache
from typing import Optional, Dict, List, Any

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, status, Request, Response

from app.api.utils import API_functools
from app.api.api_v1.models.pydantic import PartialComment
from app.api.api_v1.models.tortoise import Comment, Person


router = APIRouter()


@cache
@router.get("/", status_code=status.HTTP_200_OK)
async def comments(
    request: Request,
    res: Response,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:

    """Get all comments or some of them using 'offset' and 'limit'\n

    Args:\n
        limit (int, optional): max number of returned comments. \
        Defaults to 100.\n
        offset (int, optional): first comment to return (use with limit). \
        Defaults to 1.\n
        sort (str, optional): the order of the result. \
        attribute:(asc {ascending} or desc {descending}). \
        Defaults to "id:asc".\n
    Returns:\n
        Optional[List[Dict[str, Any]]]: list of comments found or \
        Dict with error\n
    """
    response = {
        "success": False,
        "comments": [],
    }
    order_by = API_functools.valid_order(Comment, sort)

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
    nb_comments = await Comment.all().count()

    comments = jsonable_encoder(
        await Comment.all()
        .limit(limit)
        .offset(offset)
        .order_by(order_by)
        .values(*API_functools.get_attributes(Comment))
    )

    if len(comments) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return API_functools.manage_next_previous_page(
        request, comments, nb_comments, limit, offset, data_type="comments"
    )


@cache
@router.get("/{comment_ID}", status_code=status.HTTP_200_OK)
async def comments_by_ID(res: Response, comment_ID: int) -> Dict[str, Any]:
    """Get comment by ID\n

    Args:\n
        comment_ID (int): comment ID\n
    Returns:\n
        Dict[str, Any]: contains comment found\n
    """

    comment = jsonable_encoder(
        await Comment.filter(pk=comment_ID).values(
            *API_functools.get_attributes(Comment)
        )
    )
    data = {
        "success": True,
        "comment": API_functools.get_or_default(comment, index=0, default={}),
    }
    if len(comment) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Not Found"
    return data


@cache
@router.get("/user/{user_ID}", status_code=status.HTTP_200_OK)
async def comments_by_user(res: Response, user_ID: int) -> Dict[str, Any]:
    """Get comment by ID\n

    Args:\n
        comment_ID (int): comment ID\n
    Returns:\n
        Dict[str, Any]: contains comment found\n
    """
    data = {
        "success": True,
        "comments": [],
    }

    person = await Person.filter(pk=user_ID).first()

    if person is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Comment owner doesn't exist"
        return data

    data["comments"] = jsonable_encoder(
        await Comment.filter(user_id=user_ID).values(
            *API_functools.get_attributes(Comment)
        )
    )

    if len(data["comments"]) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Not Found"
    return data


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_comment(res: Response, comment: dict) -> Dict[str, Any]:
    """Create new comment\n

    Args:\n
        comment (dict): Comment to create\n

    Returns:\n
        Dict[str, Any]: Comment created\n
    """
    data = {
        "success": True,
        "comment": {},
        "detail": "Comment successfully created",
    }
    comment_owner = API_functools.get_or_default(
        await Person.filter(pk=comment.get("user", 0)), 0, None
    )

    if comment_owner is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Comment owner doesn't exist"
        return data
    comment["user"] = comment_owner
    data["comment"] = API_functools.tortoise_to_dict(
        await Comment.create(**comment)
    )
    return jsonable_encoder(data)


@cache
@router.patch("/{comment_ID}", status_code=status.HTTP_202_ACCEPTED)
async def fix_comment(
    res: Response, comment_ID: int, comment_data: PartialComment
) -> Dict[str, Any]:
    """Fix some comment attributes according to PartialComment class\n

    Args:\n
        comment_ID (int): user ID\n
        comment_data (PartialComment): new data\n

    Returns:\n
        Dict[str, Any]: contains updated Comment data or error\n
    """
    response = {"success": True, "comment": {}}

    comment_found = await Comment.get_or_none(id=comment_ID)
    if comment_found is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["success"] = False
        response["detail"] = f"Comment with ID {comment_ID} doesn't exist."
        return response

    comment_updated = comment_found.update_from_dict(comment_data.__dict__)
    await comment_updated.save()
    response["detail"] = "Comment successfully patched"
    response["comment"] = API_functools.tortoise_to_dict(comment_updated)
    return jsonable_encoder(response)
