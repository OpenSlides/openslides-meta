import hashlib
import os
import re
from collections.abc import Callable
from enum import Enum
from typing import Any, TypedDict, cast

import requests
import yaml

KEYSEPARATOR = "/"


class TableFieldType:
    def __init__(
        self,
        table: str,
        column: str,
        field_def: dict[str, Any] | None,
        ref_column: str = "id",
    ):
        self.table = table
        self.column = column
        self.field_def: dict[str, Any] = field_def or {}
        self.ref_column = ref_column

    @property
    def collectionfield(self) -> str:
        if self.table:
            return f"{self.table}{KEYSEPARATOR}{self.column}"
        else:
            return "-"

    @staticmethod
    def get_definitions_from_foreign(
        to: str | None, reference: str | None
    ) -> "TableFieldType":
        tname = ""
        fname = ""
        tfield: dict[str, Any] = {}
        ref_column = ""
        if to:
            tname, fname, tfield = InternalHelper.get_field_definition_from_to(to)
            ref_column = "id"
        if reference:
            tname, ref_column = InternalHelper.get_foreign_key_table_column(reference)

        return TableFieldType(tname, fname, tfield, ref_column)


class ToDict(TypedDict):
    """Defines the dict keys for the to-Attribute of generic relations in field definitions"""

    collections: list[str]
    field: str


class FieldSqlErrorType(Enum):
    FIELD = 1
    SQL = 2
    ERROR = 3


class HelperGetNames:
    MAX_LEN = 63
    trigger_unique_list: list[str] = []

    @staticmethod
    def max_length(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> str:  # type:ignore
            name = func(*args, **kwargs)
            assert (
                len(name) <= HelperGetNames.MAX_LEN
            ), f"Generated name '{name}' to long in function {func}!"
            return name

        return wrapper

    @staticmethod
    def get_initial_letters(words: str) -> str:
        """get only the initial letters of words, separated by _,
        if the given string has more than 25 letters
        """
        if len(words) > 25:
            return "".join([word[0] for word in words.split("_")])
        else:
            return words

    @staticmethod
    @max_length
    def get_table_name(table_name: str) -> str:
        """get's the table name as old collection name with appendix '_t'"""
        return table_name + "_t"

    @staticmethod
    @max_length
    def get_view_name(table_name: str) -> str:
        """get's the name of a view, usually the old collection name"""
        if table_name in ("group", "user"):
            return table_name + "_"
        return table_name

    @staticmethod
    @max_length
    def get_nm_table_name(own: TableFieldType, foreign: TableFieldType) -> str:
        """get's the table name n:m-relations intermediate table"""
        if (f"{own.table}_{own.column}") < (f"{foreign.table}_{foreign.column}"):
            return f"nm_{own.table}_{HelperGetNames.get_initial_letters(own.column)}_{foreign.table}"
        else:
            return f"nm_{foreign.table}_{HelperGetNames.get_initial_letters(foreign.column)}_{own.table}"

    @staticmethod
    @max_length
    def get_gm_table_name(table_field: TableFieldType) -> str:
        """get's th table name for generic-list:many-relations intermediate table"""
        return f"gm_{table_field.table}_{table_field.column}"

    @staticmethod
    @max_length
    def get_field_in_n_m_relation_list(
        own_table_field: TableFieldType, foreign_table_name: str
    ) -> str:
        """get's the field name in a n:m-intermediate table.
        If both sides of the relation are in same table, the field name without 's' is used,
        otherwise the related tables names are used
        """
        if own_table_field.table == foreign_table_name:
            return own_table_field.column[:-1]
        else:
            return f"{own_table_field.table}_id"

    @staticmethod
    @max_length
    def get_gm_content_field(table: str, field: str) -> str:
        """Gets the name of content field in an generic:many intermediate table"""
        return f"{table}_{field}_id"

    @staticmethod
    @max_length
    def get_generic_valid_constraint_name(
        fname: str,
    ) -> str:
        """gets the name of a generic valid constraint"""
        return f"valid_{fname}_part1"

    @staticmethod
    @max_length
    def get_generic_unique_constraint_name(
        own_table_name_with_ref_column: str, own_table_column: str
    ) -> str:
        """gets the name of a generic unique constraint
        Params:
        - {table_name}_{ref_column}
        - {owcolumn}
        """
        return f"unique_${own_table_name_with_ref_column}_${own_table_column}"

    @staticmethod
    @max_length
    def get_check_enum_constraint_name(
        table_name: str,
        fname: str,
    ) -> str:
        """gets the name of check enum constraint"""
        return f"enum_{table_name}_{fname}"

    @staticmethod
    @max_length
    def get_minimum_constraint_name(
        fname: str,
    ) -> str:
        """gets the name of minimum constraint"""
        return f"minimum_{fname}"

    @staticmethod
    @max_length
    def get_minlength_constraint_name(
        fname: str,
    ) -> str:
        """gets the name of minLength constraint"""
        return f"minlength_{fname}"

    @staticmethod
    @max_length
    def get_not_null_rel_list_insert_trigger_name(
        table_name: str,
        column_name: str,
    ) -> str:
        """gets the name of the insert trigger for not null on relation lists"""
        name = f"tr_i_{table_name}_{column_name}"[: HelperGetNames.MAX_LEN]
        if name in HelperGetNames.trigger_unique_list:
            raise Exception(f"trigger {name} is not unique!")
        HelperGetNames.trigger_unique_list.append(name)
        return name

    @staticmethod
    @max_length
    def get_not_null_rel_list_upd_del_trigger_name(
        table_name: str,
        column_name: str,
    ) -> str:
        """gets the name of the update/delete trigger for not null on relation lists"""
        name = f"tr_ud_{table_name}_{column_name}"[: HelperGetNames.MAX_LEN]
        if name in HelperGetNames.trigger_unique_list:
            raise Exception(f"trigger {name} is not unique!")
        HelperGetNames.trigger_unique_list.append(name)
        return name

    @staticmethod
    @max_length
    def get_notify_trigger_name(
        table_name: str,
    ) -> str:
        """gets the name of the trigger for notifying changes on models"""
        name = f"tr_notify_{table_name}"[: HelperGetNames.MAX_LEN]
        if name in HelperGetNames.trigger_unique_list:
            raise Exception(f"trigger {name} is not unique!")
        HelperGetNames.trigger_unique_list.append(name)
        return name

    @staticmethod
    @max_length
    def get_notify_related_trigger_name(
        table_name: str,
        column_name: str,
    ) -> str:
        """gets the name of the trigger for notifying changes on related models"""
        name = f"tr_notify_rel_{table_name}_{column_name}"[: HelperGetNames.MAX_LEN]
        if name in HelperGetNames.trigger_unique_list:
            raise Exception(f"trigger {name} is not unique!")
        HelperGetNames.trigger_unique_list.append(name)
        return name


class InternalHelper:
    MODELS: dict[str, dict[str, Any]] = {}
    checksum: str = ""
    ref_compiled = compiled = re.compile(r"(^\w+\b).*?\((.*?)\)")

    @classmethod
    def read_models_yml(cls, file: str) -> tuple[dict[str, Any], str]:
        """method reads modesl.yml from file or web and returns MODELS and it's checksum"""
        if os.path.isfile(file):
            with open(file, "rb") as x:
                models_yml = x.read()
        else:
            models_yml = requests.get(file).content

        # calc checksum to assert the schema.sql is up-to-date
        checksum = hashlib.md5(models_yml).hexdigest()

        # Fix broken keys
        models_yml = models_yml.replace(b" yes:", b' "yes":')
        models_yml = models_yml.replace(b" no:", b' "no":')

        # Load and parse models.yml
        cls.MODELS = yaml.safe_load(models_yml)
        cls.check_field_length()
        return cls.MODELS, checksum

    @classmethod
    def check_field_length(cls) -> None:
        to_long: list[str] = []
        for table_name, fields in cls.MODELS.items():
            if table_name in ["_migration_index", "_meta"]:
                continue
            for fname in fields.keys():
                if len(fname) > HelperGetNames.MAX_LEN:
                    to_long.append(f"{table_name}.{fname}:{len(fname)}")
        if to_long:
            raise Exception("\n".join(to_long))

    @staticmethod
    def get_field_definition_from_to(to: str) -> tuple[str, str, dict[str, Any]]:
        tname, fname = to.split("/")
        try:
            field = InternalHelper.get_models(tname, fname)
        except Exception:
            raise Exception(
                f"Exception on splitting to {to} in get_field_definition_from_to"
            )
        assert (
            len(tname) <= HelperGetNames.MAX_LEN
        ), f"Generated tname '{tname}' to long in function 'get_field_definition_from_to'!"
        assert (
            len(fname) <= HelperGetNames.MAX_LEN
        ), f"Generated fname '{fname}' to long in function 'get_field_definition_from_to'!"

        return tname, fname, field

    @staticmethod
    def get_foreign_key_table_column(reference: str | None) -> tuple[str, str]:
        """
        Returns a tuple (table_name, field_name) gotten from "reference"-attribut
        """
        if reference:
            result = InternalHelper.ref_compiled.search(reference)
            if result is None:
                return reference.strip(), "id"
            re_groups = result.groups()
            cols = re_groups[1]
            if cols:
                cols = ",".join([col.strip() for col in cols.split(",")])
            else:
                cols = "id"
            return re_groups[0], cols
        else:
            raise Exception("Relation field without reference")

    @classmethod
    def get_models(cls, collection: str, field: str) -> dict[str, Any]:
        if cls.MODELS:
            try:
                return cls.MODELS[collection][field]
            except KeyError:
                raise Exception(f"MODELS field {collection}.{field} doesn't exist")
        raise Exception("You have to initialize models in class InternalHelper")

    @staticmethod
    def get_cardinality(field_all: TableFieldType) -> tuple[str, str]:
        """
        Returns
        - string with cardinality string (1, 1G, n or nG= Cardinality, G=Generatic-relation, r=reference, t=to, s=sql, R=required)
        - string with error message or empty string if no error
        """
        error = ""
        field = field_all.field_def
        if field:
            required = bool(field.get("required"))
            sql = "sql" in field
            to = bool(field.get("to"))
            reference = bool(field.get("reference"))

            # general rules of inconsistent field descriptions on field level
            if reference and not to:  # temporaray rule to keep all to-attributes
                error = "Field with reference temporarely needs also to-attribute\n"
            elif field.get("sql") == "":
                error = "sql attribute may not be empty\n"
            elif required and sql:
                error = "Field with attribute sql cannot be required\n"
            elif not (to or reference):
                error = "Relation field must have `to` or `reference` attribut set\n"
            elif field["type"] == "generic-relation-list" and required:
                error = "generic-relation-list cannot be required: not implemented\n"

            if field["type"] == "relation":
                result = "1"
            elif field["type"] == "relation-list":
                result = "n"
            elif field["type"] == "generic-relation":
                result = "1G"
            elif field["type"] == "generic-relation-list":
                result = "nG"
            else:
                raise Exception(
                    f"Not implemented type {field['type']} in method get_cardinality found!"
                )
            if reference:
                result += "r"
            if (
                to and not reference
            ):  # to with reference only for temporaray backup compatibility in backend relation-handling
                result += "t"
            if required:
                result += "R"
            if sql:
                result += "s"
        else:
            result = ""
        return result, error

    @staticmethod
    def generate_field_or_sql_decision(
        own: TableFieldType, own_c: str, foreign: TableFieldType, foreign_c: str
    ) -> tuple[FieldSqlErrorType, bool, str]:
        """
        Returns:
        - field, sql, error for own => enum FieldSqlErrorType
        - primary field for own: (only relevant for list fields)
        - error line if error else empty string
        """
        decision_list: dict[
            tuple[str, str], tuple[FieldSqlErrorType | None, bool | str | None]
        ] = {
            ("1Gr", ""): (FieldSqlErrorType.FIELD, False),
            ("1GrR", ""): (FieldSqlErrorType.FIELD, False),
            ("1r", ""): (FieldSqlErrorType.FIELD, False),
            ("1rR", ""): (FieldSqlErrorType.FIELD, False),
            ("1t", "1GrR"): (FieldSqlErrorType.SQL, False),
            ("1t", "1r"): (FieldSqlErrorType.SQL, False),
            ("1t", "1rR"): (FieldSqlErrorType.SQL, False),
            ("1tR", "1Gr"): (FieldSqlErrorType.SQL, False),
            ("1tR", "1GrR"): (FieldSqlErrorType.SQL, False),
            ("nGt", "nt"): (FieldSqlErrorType.SQL, True),
            ("nr", ""): (FieldSqlErrorType.SQL, True),
            ("nt", "1Gr"): (FieldSqlErrorType.SQL, False),
            ("nt", "1GrR"): (FieldSqlErrorType.SQL, False),
            ("nt", "1r"): (FieldSqlErrorType.SQL, False),
            ("nt", "1rR"): (FieldSqlErrorType.SQL, False),
            ("nt", "nGt"): (FieldSqlErrorType.SQL, False),
            ("nt", "nt"): (FieldSqlErrorType.SQL, "primary_decide_alphabetical"),
            ("ntR", "1r"): (FieldSqlErrorType.SQL, False),
            ("nts", "nts"): (FieldSqlErrorType.SQL, False),
        }

        foreign_c_replacement_list: list[str] = [
            "1Gr",
            "1GrR",
            "1r",
            "1rR",
            "nr",
        ]

        state: FieldSqlErrorType | str | None
        primary: bool | str | None
        error = ""

        if own_c in foreign_c_replacement_list:
            foreign_c = ""

        state, primary = decision_list.get((own_c, foreign_c), (None, None))
        if state is None:
            error = f"Type combination not implemented: {own_c}:{foreign_c} on field {own.collectionfield}\n"
            state = FieldSqlErrorType.ERROR
        elif primary == "primary_decide_alphabetical":
            primary = (
                own.collectionfield == foreign.collectionfield
                or foreign.collectionfield == "-"
                or own.collectionfield < foreign.collectionfield
            )
        return cast(FieldSqlErrorType, state), cast(bool, primary), error

    @staticmethod
    def check_relation_definitions(
        own_field: TableFieldType, foreign_fields: list[TableFieldType]
    ) -> tuple[FieldSqlErrorType, bool, str, str]:
        """
        Decides for the own-field,
          - whether it is a field, a sql-expression or is there an error
          - relation-list and generic-relation-list are always sql-expressions.
            True significates, that it is the pimary that creates the intermediate table

        Also checks relational behaviour and produces the informative relation line and in
        case of an error an error text

        Returns:
        - field, sql, error => enum FieldSqlErrorType
        - primary field (only relevant for list fields)
        - complete relational text with FIELD, SQL or *** in front
        - error line if error else empty string
        """
        error = ""
        own_c, tmp_error = InternalHelper.get_cardinality(own_field)
        error = error or tmp_error
        foreigns_c = []
        foreign_collectionfields = []
        for foreign_field in foreign_fields:
            foreign_c, tmp_error = InternalHelper.get_cardinality(foreign_field)
            foreigns_c.append(foreign_c)
            error = error or tmp_error
            foreign_collectionfields.append(foreign_field.collectionfield)

        if error:
            state = FieldSqlErrorType.ERROR
            primary = False
        else:
            for i, foreign_field in enumerate(foreign_fields):
                if i == 0:
                    state, primary, error = (
                        InternalHelper.generate_field_or_sql_decision(
                            own_field, own_c, foreign_field, foreigns_c[i]
                        )
                    )
                else:
                    statex, primaryx, error = (
                        InternalHelper.generate_field_or_sql_decision(
                            own_field, own_c, foreign_field, foreigns_c[i]
                        )
                    )
                    if not error and (statex != state or primaryx != primary):
                        error = f"Error in generation for generic collectionfield '{own_field.collectionfield}'"
                if error:
                    state = FieldSqlErrorType.ERROR
                    break

        state_text = "***" if state == FieldSqlErrorType.ERROR else state.name
        text = f"{state_text} {own_c}:{','.join(foreigns_c)} => {own_field.collectionfield}:-> {','.join(foreign_collectionfields)}\n"
        if state == FieldSqlErrorType.ERROR:
            text += f"    {error}"
        return state, primary, text, error

    @staticmethod
    def get_definitions_from_foreign_list(
        to: ToDict | list[str] | None,
        reference: list[str] | None,
    ) -> list[TableFieldType]:
        """
        used for generic_relation with multiple foreign relations
        """
        # temporarely allowed
        # if to and reference:
        #     raise Exception(
        #         f"Field {table}/{field}: On generic-relation fields it is not allowed to use 'to' and 'reference' for 1 field"
        #     )
        results: list[TableFieldType] = []
        # precedence for reference
        if reference:
            for ref in reference:
                results.append(TableFieldType.get_definitions_from_foreign(None, ref))
        elif isinstance(to, dict):
            fname = "/" + to["field"]
            for table in to["collections"]:
                results.append(
                    TableFieldType.get_definitions_from_foreign(table + fname, None)
                )
        elif isinstance(to, list):
            for collectionfield in to:
                results.append(
                    TableFieldType.get_definitions_from_foreign(collectionfield, None)
                )
        else:
            results.append(TableFieldType.get_definitions_from_foreign(to, None))
        return results
