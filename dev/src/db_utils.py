from typing import Any

from .python_sql import Column, Table


class DbUtils:
    @classmethod
    def get_columns_and_values_for_insert(
        cls,
        table: Table,
        data_list: list[dict[str, Any]],
    ) -> tuple[list[Column], list[list[Any | None]]]:
        """
        takes a list of dicts, each one to be inserted
        Takes care of columns and row positions and fills
        not existent columns in row with "None"
        """
        if not data_list:
            return [], []
        # use all keys in same sequence
        keys_set: set = set()
        for data in data_list:
            keys_set.update(data.keys())
        keys: list = sorted(keys_set)
        columns = [Column(table, key) for key in keys]
        values = [[row.get(k, None) for k in keys] for row in data_list]
        return columns, values

    @classmethod
    def get_columns_from_list(cls, table: Table, items: list[str]) -> list[Column]:
        return [Column(table, item) for item in items]

    @classmethod
    def get_pg_array_for_cu(cls, data: list) -> str:
        """converts a value list into string used for complete array field"""
        return f"""{{"{'","'.join(item for item in data)}"}}"""
