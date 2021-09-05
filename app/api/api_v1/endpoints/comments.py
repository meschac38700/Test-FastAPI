from functools import cache
from typing import Optional, Dict, List, Any

from tortoise.functions import Count
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, status, Request, Response

from app.api.utils import API_functools
from app.api.api_v1.models.pydantic import (
    PartialComment,
    Comment as CommentBaseModel,
)
from app.api.api_v1.models.tortoise import Comment, Person


router = APIRouter()


async def filter_comments(
    req: Request,
    res: Response,
    max_comments: int,
    filters: Optional[dict] = None,
    offset: Optional[int] = 20,
    limit: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
):
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
    comments = await API_functools.add_owner_fullname(
        jsonable_encoder(
            await (Comment.all() if filters is None else Comment.filter(**filters))
            .prefetch_related("vote")
            .prefetch_related("children")
            .annotate(votes=Count("vote", distinct=True))
            .annotate(nb_children=Count("children", distinct=True))
            .limit(limit)
            .offset(offset)
            .order_by(order_by)
            .values(*API_functools.get_attributes(Comment), "votes", "nb_children")
        )
    )

    if len(comments) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return API_functools.manage_next_previous_page(
        req, comments, max_comments, limit, offset, data_type="comments"
    )


@cache
@router.get("/", status_code=status.HTTP_200_OK)
async def comments(
    req: Request,
    res: Response,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
    parents: bool = False,
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
        parents (bool): get only parents comments. Defaults to False
    Returns:\n
        Optional[List[Dict[str, Any]]]: list of comments found or \
        Dict with error\n
    """
    max_comments = await Comment.all().count()
    if parents:
        max_comments = await Comment.filter(parent_id=None).count()
        return await filter_comments(
            req,
            res,
            max_comments,
            offset=offset,
            limit=5,
            sort=sort,
            filters={"parent_id": None},
        )

    return await filter_comments(
        req, res, max_comments, offset=offset, limit=limit, sort=sort
    )


@cache
@router.get("/{comment_ID}", status_code=status.HTTP_200_OK)
async def comments_by_ID(
    res: Response, comment_ID: int, children: bool = False
) -> Dict[str, Any]:
    """Get comment by ID\n

    Args:\n
        comment_ID (int): comment ID\n
        children (bool): get current comment children
    Returns:\n
        Dict[str, Any]: contains comment found\n
    """
    key, value = ("comment", {}) if not children else ("children", [])
    data = {"success": True, key: value, "detail": "Successful operation"}

    if not await Comment.exists(pk=comment_ID):
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Not Found"
        return data

    if children:
        data["children"] = await API_functools.add_owner_fullname(
            await (await Comment.filter(pk=comment_ID).first()).json_children()
        )
    else:
        comment = jsonable_encoder(
            await Comment.filter(pk=comment_ID)
            .prefetch_related("vote")
            .prefetch_related("children")
            .annotate(votes=Count("vote", distinct=True))
            .annotate(nb_children=Count("children", distinct=True))
            .values(*API_functools.get_attributes(Comment), "votes", "nb_children")
        )

        data["comment"] = API_functools.get_or_default(comment, index=0, default={})
        if len(data["comment"].keys()) > 0:
            data["comment"] = API_functools.get_or_default(
                await API_functools.add_owner_fullname([data["comment"]]),
                index=0,
                default={},
            )

    return data


@cache
@router.get("/user/{user_ID}", status_code=status.HTTP_200_OK)
async def comments_by_user(
    req: Request,
    res: Response,
    user_ID: int,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:

    """Get all user comments or some of them using 'offset' and 'limit'\n

    Args:\n
        user_ID (int): user ID
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
    person = await Person.filter(pk=user_ID).first()

    if person is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {
            "success": False,
            "comments": [],
            "detail": "Comment owner doesn't exist",
        }

    max_comments = await Comment.filter(user_id=user_ID).count()

    return await filter_comments(
        req,
        res,
        max_comments,
        filters={"user_id": user_ID},
        offset=offset,
        limit=limit,
        sort=sort,
    )


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
    data["comment"] = API_functools.tortoise_to_dict(await Comment.create(**comment))
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


@cache
@router.put("/{comment_ID}", status_code=status.HTTP_202_ACCEPTED)
async def update_comment(
    res: Response, comment_ID: int, comment_data: CommentBaseModel
) -> Dict[str, Any]:
    """Update comment attributes according to CommentBaseModel class\n

    Args:\n
        comment_ID (int): comment to update\n
        comment_data (CommentBaseModel): new comment data\n

    Returns:\n
        Dict[str, Any]: contains comment new data or error\n
    """
    response = {"success": True, "comment": {}}

    new_owner = await Person.get_or_none(id=comment_data.user)
    if new_owner is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["success"] = False
        response["detail"] = "Comment owner doesn't exist."
        return response

    comment_found = await Comment.get_or_none(id=comment_ID)
    if comment_found is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["success"] = False
        response["detail"] = f"Comment with ID {comment_ID} doesn't exist."
        return response

    comment_data.user = new_owner

    comment_updated = comment_found.update_from_dict(comment_data.__dict__)
    await comment_updated.save()
    response["detail"] = "Comment successfully updated"
    response["comment"] = API_functools.tortoise_to_dict(comment_updated)
    return jsonable_encoder(response)


@router.delete("/{comment_ID}", status_code=status.HTTP_202_ACCEPTED)
async def delete_comment(res: Response, comment_ID: int) -> Dict[str, Any]:
    """Delete a comment\n

    Args:\n
        comment_ID (int): comment to delete\n

    Returns:\n
        Dict[str, Any]: contains deleted comment data or error\n
    """
    response = {"success": False, "comment": {}}

    comment_found = await Comment.get_or_none(id=comment_ID)
    if comment_found is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["detail"] = f"Comment with ID {comment_ID} doesn't exist"
        return response

    await comment_found.delete()

    response["success"] = True
    response["comment"] = API_functools.tortoise_to_dict(comment_found)
    response["detail"] = f"Comment {comment_ID} deleted successfully ⭐"
    return jsonable_encoder(response)
