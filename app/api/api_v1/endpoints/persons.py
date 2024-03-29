from functools import cache
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Request, Response, status

from app.api.api_v1.storage.database import Database
from app.api.utils import API_functools
from app.api.api_v1.models.pydantic import User, PartialUser
from app.api.api_v1.models.tortoise import Person, Person_Pydantic

router = APIRouter()


@cache
@router.get("/", status_code=status.HTTP_200_OK)
async def users(
    request: Request,
    res: Response,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort: Optional[str] = "id:asc",
) -> Optional[List[Dict[str, Any]]]:
    """Get all users or some of them using 'offset' and 'limit'

    Args:

        limit (int, optional): max number of returned users.
        Defaults to 100.
        offset (int, optional): first user to return (use with limit).
        Defaults to 1.
        sort (str, optional): the order of the result.
        attribute:(asc {ascending} or desc {descending}).
        Defaults to "id:asc".

    Returns:

        Optional[List[Dict[str, Any]]]: list of users found or
        Dict with error
    """
    response = {
        "success": False,
        "users": [],
    }
    order_by = API_functools.valid_order(Person, sort)
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
    nb_users = await Person.all().count()

    users = await Person_Pydantic.from_queryset(
        Person.all().limit(limit).offset(offset).order_by(order_by)
    )

    if len(users) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return API_functools.manage_next_previous_page(
        request, users, nb_users, limit, offset
    )


@cache
@router.get("/{user_ID}", status_code=status.HTTP_200_OK)
async def users_by_ID(res: Response, user_ID: int) -> Dict[str, Any]:
    """Get user by ID

    Args:

        user_ID (int): user ID

    Returns:

        Dict[str, Any]: user found or Error
    """
    user = await Person_Pydantic.from_queryset(Person.filter(pk=user_ID))
    data = {
        "success": True,
        "user": API_functools.get_or_default(user, 0, {}),
    }
    if not API_functools.instance_of(data["user"], Person):
        res.status_code = status.HTTP_404_NOT_FOUND
        data["success"] = False
        data["detail"] = "Not Found"
    return data


@cache
@router.get("/filter/{user_attribute}/{value}", status_code=status.HTTP_200_OK)
async def users_by_attribute(
    res: Response, user_attribute: Any, value: Any
) -> List[Dict[str, Any]]:
    """Get user by attribute except

    Args:

        user_attribute (Any): user's attribute
        you can combine two or more attributes with keywords "Or", "And"
        ex: idOremail, genderAndemail

    Returns:
        List[Dict[str, Any]]: List of users found
    """
    response = {"success": False, "users": []}
    lower_user_attribute = user_attribute.lower()
    if (
        "and" not in lower_user_attribute and "or" not in lower_user_attribute
    ) and not API_functools.is_attribute_of(user_attribute, Person):
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {
            **response,
            "detail": f"""
            Invalid attribute filter.
            Try with: {API_functools.get_attributes(Person)}
            """,
        }
    query_builder = Database.query_filter_builder(user_attribute, value)

    persons = await Person_Pydantic.from_queryset(
        Person.filter(*query_builder).order_by("id")
    )
    if len(persons) == 0:
        res.status_code = status.HTTP_404_NOT_FOUND
        return {**response, "detail": "Not Found"}

    return {"success": True, "users": persons}


@router.post("/", response_model=Person_Pydantic, status_code=status.HTTP_201_CREATED)
async def create_user(user: User) -> Dict[str, Any]:
    """Create new user

    Args:
        user (User): user data according to User model

    Returns:

        Dict[str, Any]: User created
    """
    user = await Person.create(**user.__dict__)
    return user


@cache
@router.patch("/{user_ID}", status_code=status.HTTP_202_ACCEPTED)
async def fix_user(res: Response, user_ID: int, user: PartialUser) -> Dict[str, Any]:
    """Fix some user attributes according to PartialUser class

    Args:

        user_ID (int): user ID
        user_data (User): new data

    Returns:

        Dict[str, Any]: User patched or error if not exists
    """
    response = {"success": False, "user": {}}

    """(More control to the validator)
    Prefer this method to use the Pydantic validator \
    which is more maintainable
    than the tortoiseORM validator in my opinion
    see: https://pydantic-docs.helpmanual.io/usage/validators/
    """
    user_found = await Person.get_or_none(id=user_ID)
    if user_found is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["detail"] = f"User with ID {user_ID} doesn't exist."
        return response

    user_updated = user_found.update_from_dict({**user.__dict__, "id": user_found.id})
    await user_updated.save()
    return await Person_Pydantic.from_tortoise_orm(user_updated)


@cache
@router.put("/{user_ID}", status_code=status.HTTP_202_ACCEPTED)
async def update_user(res: Response, user_ID: int, new_data: User) -> Dict[str, Any]:
    """Update user attributes according to User class

    Args:

        user_ID (int): user to update
        new_data (User): new user data

    Returns:

        Dict[str, Any]: user updated
    """
    response = {"success": False, "user": {}}

    # check if user exists
    curr_user = await Person.get_or_none(id=user_ID)
    if curr_user is None:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["detail"] = f"User with ID {user_ID} doesn't exist."
        return response

    curr_user = await curr_user.update_from_dict(new_data.__dict__)
    await curr_user.save()
    return await Person_Pydantic.from_tortoise_orm(curr_user)


@router.delete("/{user_ID}", status_code=status.HTTP_202_ACCEPTED)
async def delete_user(res: Response, user_ID: int) -> Dict[str, Any]:
    """Delete a user\n

    Args:\n
        user_ID (int): user to delete\n

    Returns:\n
        Dict[str, Any]: deleted User or error user not found\n
    """
    response: Dict[str, Any] = {"success": False, "user": {}}

    # TODO check permission before delete user

    user_found = await Person.get_or_none(id=user_ID)
    if not user_found:
        res.status_code = status.HTTP_404_NOT_FOUND
        response["detail"] = f"User with ID {user_ID} doesn't exist"
        return response

    await user_found.delete()

    response["success"] = True
    response["user"] = await Person_Pydantic.from_tortoise_orm(user_found)
    response["detail"] = f"User {user_ID} delete successfully ⭐"

    return response
