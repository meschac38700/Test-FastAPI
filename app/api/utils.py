import re
import concurrent.futures as futures
from typing import Optional, Dict, Any, Type, TypeVar, List

from tortoise.models import Model as TortoiseModel
from tortoise.fields.relational import RelationalField

from .api_v1.storage.initial_data import INIT_DATA
from .api_v1.models.tortoise import Person, Comment

ORDERS: Dict[str, str] = {"asc": "", "desc": "-"}
MODEL = TypeVar("MODEL", bound="API_functools")


class API_functools:
    @classmethod
    async def add_owner_fullname(
        cls: Type[MODEL], data: list[dict[str, Any]], key_name="owner_fullname"
    ) -> list[dict[str, Any]]:
        """Add owner fullname (first_name + last_name) to every object in given data
        if every object, in data list, contains "user_id" key otherwise
        return given data list without changes

        Args:

            cls (API_functools): utility class that used to call this method
            data (list[dict]): data to process
            key_name (str, optional): key name of owner fullname. Defaults to
            "owner_fullname".

        Returns:

            list[dict[str, Any]]:
        """
        user_IDs = [c.get("user_id", None) for c in data]
        if len(data) == 0 or None in user_IDs:
            return data
        owners = await (
            Person.filter(pk__in=map(lambda pk: pk, user_IDs)).values(
                "id", "first_name", "last_name"
            )
        )

        new_data = []
        owner = {}
        for cmt in data:
            if owner.get("id", 0) != cmt["user_id"]:
                owner = tuple(
                    filter(lambda owner: owner["id"] == cmt["user_id"], owners)
                )[0]

            new_data.append(
                {**cmt, "owner_fullname": f"{owner['first_name']} {owner['last_name']}"},
            )

        return new_data

    @classmethod
    def tortoise_to_dict(cls: Type[MODEL], instance: TortoiseModel) -> dict[str, Any]:
        """Return attributes from Tortoise model as a dict[attr, value]

        Args:

            cls (API_functools): utility class that used to call this method
            instance (TortoiseModel): Tortoise instance

        Returns:

            dict: {attr: value, ...}
        """

        return {
            key: value
            for key, value in instance.__dict__.items()
            if key in API_functools.get_attributes(instance.__class__)
        }

    @classmethod
    def strip_spaces(cls: Type[MODEL], string: str) -> str:
        """Remove space at start/end and replace multiple spaces with a single space

        Args:
            string (str): string to be processed

        Returns:

            str: processed string
        """
        return re.sub(r"\s{2,}", " ", string.strip())

    @classmethod
    def get_or_default(
        cls: Type[MODEL], list_el: tuple, index: int, default: Any = None
    ) -> Any:
        """Return, from a list, element at given index or
        given default value if not exists

        Args:

            cls (API_functools): utility class that used to call this method
            list_el (tuple): list of elements
            index (int): position of searched element
            default (Any): default value if element not found in list of elements

        Returns:

            Any: element if found else default
        """
        return default if len(list_el) <= index else list_el[index]

    @classmethod
    def instance_of(
        cls: Type[MODEL], el: Any, expected_class: Type[Any], **kwargs: dict
    ) -> bool:
        """Check element is instance of given class

        Args:

            cls (API_functools): utility class that used to call this method
            el (Any): object from any class
            expected_class (Type[U]): class expected
            kwargs (dict): options
                base (bool): checking base class

        Returns:

            bool: is/not instance of given class
        """
        if kwargs.get("base", False):
            return (
                el.__class__.__base__.__name__.lower() == expected_class.__name__.lower()
            )
        return el.__class__.__name__.lower() == expected_class.__name__.lower()

    @classmethod
    def get_attributes(
        cls: Type[MODEL], target_cls: TortoiseModel, **kwargs: dict
    ) -> tuple[str]:
        """Return all attributes of given class

        Args:

            target (TortoiseModel): The class
            kwargs (dict): options
                exclude (list or tuple): attributes to exclude from attributes found
                replace (dict): attributes to replace, key(old) -> value(new)
                add (list or tuple): some attributes to add to the attributes found
                ignore_foreignKey (bool): Not return foreignKey field.
                    this not includes foreignKey id field, such as: user_id, comment_id
        Returns:

            tuple[str]: tuple of attributes found
        """
        exclude = kwargs.get("exclude", tuple())  # (attr1, attr2)
        add = kwargs.get("add", tuple())  # (new_attr1, new_attr2)
        replace = kwargs.get("replace", dict())  # {old_attr: new_attr}
        attributes = tuple(target_cls._meta.fields_map.keys())
        if kwargs.get("ignore_foreignKey", True):  # Exclude foreignKey
            exclude += tuple(
                (
                    fk
                    for fk, model in target_cls._meta.fields_map.items()
                    if cls.instance_of(model, RelationalField, base=True)
                )
            )
        for old, new in replace.items():
            attributes = tuple(map(lambda attr: new if attr == old else attr, attributes))
        if type(add) in (tuple, list):
            for attr in add:
                attributes += (attr,)
        if type(exclude) in (tuple, list):
            attributes = tuple(filter(lambda attr: attr not in exclude, attributes))
        return attributes

    @classmethod
    def valid_order(
        cls: Type[MODEL], target_cls: TortoiseModel, sort: str, **kwargs: dict
    ) -> Optional[str]:
        """Validator for given sort that will be used to sort db result.
        Format: attribute:direction(asc or desc), ex: id:asc

        Args:

            cls (API_functools): utility class that used to call this method
            target_cls (TortoiseModel): model for db data
            sort (str): string to valid from http request
            kwargs (dict): Options

        Returns:

            Optional[str]: valid sql string order by or None
        """
        if ":" not in sort:
            return None
        attr, order = sort.lower().split(":")
        valid_attributes = ("id",) + cls.get_attributes(target_cls, **kwargs)
        if attr in valid_attributes and order in ORDERS.keys():
            return f"{ORDERS.get(order, '')}{attr}"
        return None

    @classmethod
    def is_attribute_of(
        cls: Type[MODEL],
        attr: str,
        target_cls: TortoiseModel,
    ) -> bool:
        """Check if attr is attribute of given class

        Args:

            cls (MODEL): utility class that used to call this method
            target_cls (TortoiseModel): model for db data
            attr (str): attribute to check

        Returns:

            bool: is/not valid attribute
        """
        return attr.lower() in cls.get_attributes(target_cls)

    @classmethod
    def manage_next_previous_page(
        cls,
        request,
        data: List[Dict],
        nb_total_data: int,
        limit: int,
        offset: int,
        data_type: str = "users",
    ) -> Dict[str, Any]:
        """Add next and previous urls to manage response pagination

        Args:

            request (Request): current request
            data (Dict[str, Any]): request response data
            nb_total_data (int): total number of resources from DB
            limit (int): limit quantity of returned data
            offset (int): offset of returned data
            data_type (str): type of data, Default to users.

        Returns:

            Dict[str, Any]: response
        """
        _data = {"success": len(data) > 0, "next": None, "previous": None}
        _data[data_type] = data

        # manage next data
        base = request.scope.get("path")
        # retrieve query string (GET params)
        query_string = f'&{(request.scope.get("query_string") or b"").decode("utf-8")}'
        query_string = (
            "&".join(
                filter(
                    lambda query: "limit" not in query and "offset" not in query,
                    query_string.split("&"),
                )
            )
            if len(query_string) > 1
            else ""
        )

        if offset + limit < nb_total_data and limit <= nb_total_data:
            next_offset = offset + limit
            _data["next"] = f"{base}?limit={limit}&offset={next_offset}{query_string}"

        # manage previous data
        if offset - limit >= 0 and limit <= nb_total_data:
            previous_offset = offset - limit
            _data[
                "previous"
            ] = f"{base}?limit={limit}&offset={previous_offset}{query_string}"
        return _data

    @classmethod
    async def insert_default_data(
        cls: Type[MODEL],
        table: Optional[str] = None,
        data: Optional[dict] = INIT_DATA,
        quantity: int = -1,
    ) -> None:
        """Init tables with some default fake data

        Args:

            table (str): specific table to manage, Default to None == all
            data ([dict], optional): data to load. Defaults to INIT_DATA.
            quantity (int, optional): quantity of data to load. Defaults to -1.

        Returns:

            None
        """
        data = data[table] if table is not None and cls.instance_of(data, dict) else data

        if cls.instance_of(data, list):
            data_length = len(data)
            quantity = quantity if data_length >= quantity >= 1 else data_length
            data = data[:quantity]
            with futures.ProcessPoolExecutor() as executor:
                for obj in data:
                    executor.map(await cls._insert_default_data(table, obj))
        elif cls.instance_of(data, dict):
            for _table, _data in data.items():
                data_length = len(_data)
                quantity = quantity if data_length >= quantity >= 1 else data_length
                c_data = _data[:quantity]
                with futures.ProcessPoolExecutor() as executor:
                    for obj in c_data:
                        executor.map(await cls._insert_default_data(_table, obj))
        else:
            raise ValueError("Data must be a list or dict")

    @classmethod
    async def _insert_default_data(
        cls: Type[MODEL], table: str, _data: dict
    ) -> TortoiseModel:
        """Insert data into given table

        Args:

            table (str): table to modify
            _data (dict): data to insert according to table model

        Returns:

            TortoiseModel: inserted instance
        """
        data = {**_data}  # prevent: modify content of argument _data
        # Replace foreign attribute to an instance of foreign model
        if table.lower() == "comment" and cls.instance_of(data["user"], int):
            data["user"] = await Person.filter(id=data["user"]).first()
            data["top_parent"] = await Comment.filter(id=data["top_parent"]).first()
            data["parent"] = await Comment.filter(id=data["parent"]).first()
        elif (
            table.lower() == "vote"
            and cls.instance_of(data["user"], int)
            and cls.instance_of(data["comment"], int)
        ):

            exec("from .api_v1.models.tortoise import Vote")
            data["user"] = await Person.filter(id=data["user"]).first()
            data["comment"] = await Comment.filter(id=data["comment"]).first()

        return await eval(f"{table.capitalize()}.create(**data)")
