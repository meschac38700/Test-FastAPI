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
        cls: Type[MODEL], data: list[dict], key="owner_fullname"
    ):
        user_IDs = [c.get("user_id", None) for c in data]
        if len(data) == 0 or None in user_IDs:
            return data
        owners = await (
            Person.filter(pk__in=map(lambda pk: pk, user_IDs)).values(
                "id", "first_name", "last_name"
            )
        )

        new_data = []
        for cmt in data:
            owner = tuple(filter(lambda owner: owner["id"] == cmt["user_id"], owners))[0]
            new_data.append(
                {**cmt, "owner_fullname": f"{owner['first_name']} {owner['last_name']}"},
            )

        return new_data

    @classmethod
    def tortoise_to_dict(cls: Type[MODEL], instance: TortoiseModel):
        return {
            key: value
            for key, value in instance.__dict__.items()
            if key in API_functools.get_attributes(instance.__class__)
        }

    @classmethod
    def strip_spaces(cls: Type[MODEL], string: str) -> str:
        """Remove multiple spaces in the given string

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
        """Search element from specific list\n

        Args:\n
            cls (API_functools): utility class that used to call this method\n
            list_el (tuple): list of elements
            index (int): position of searched element
            default (Any): default value if element not found in\
                list of elements\n

        Returns:\n
            Any: element if found else default
        """
        return default if len(list_el) <= index else list_el[index]

    @classmethod
    def instance_of(
        cls: Type[MODEL], el: Any, expected_class: Type[Any], **kwargs: dict
    ) -> bool:
        """Check element is from specific class\n

        Args:\n
            cls (API_functools): utility class that used to call this method\n
            el (Any): object from any class\n
            expected_class (Type[U]): class expected\n
            kwargs (dict): options
                base (bool): checking base class

        Returns:\n
            bool: equality(True if equals else False)
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
        """Return class object attributes except ID\n

        Args:\n
            target (TortoiseModel): The class
            kwargs (dict): options
                exclude (list or tuple): attributes to exclude from attributes found
                replace (dict): attributes to replace, key(old) -> value(new)
                add (list or tuple): some attributes to add to the attributes found
                ignore_foreignKey (bool): Not return foreignKey field.
                    this not includes foreignKey id field, such as: user_id, comment_id
        Returns:
            tuple[str]: attributes
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
        """Validator for sort db query result with \
            attribute:direction(asc or desc)\n

        Args:\n
            cls (API_functools): utility class that used to call this method\n
            target_cls (TortoiseModel): model for db data\n
            sort (str): string to valid from http request\n
            kwargs (dict): Options
        Returns:\n
            Optional[str]: valid sql string order by or None
        """
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
        """Check if attr is a target_cls's attribute
           except the ID attribute\n

        Args:
            cls (MODEL): utility class that used to call this method\n
            target_cls (TortoiseModel): model for db data\n
            attr (str): attribute to check

        Returns:
            bool: is valid attribute
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
        """Manage next/previous data link(url)

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
        """Init tables with some default fake data\n

        Args:\n
            table (str): specific table to manage, Default to None == all\n
            data ([dict], optional): data to load. Defaults to INIT_DATA.\n
            quantity (int, optional): quantity of data to load. Defaults to -1.\n
        Returns:\n
            None: nothing\n
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
        """Insert data into specific table
            called by insert_default_data function\n

        Args:\n
            table (str): table to modify
            _data (dict): data to insert according to table model\n

        Returns:\n
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
