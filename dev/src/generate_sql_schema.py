import string
import sys
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from enum import Enum
from pathlib import Path
from string import Formatter
from textwrap import dedent
from typing import Any, TypedDict, cast

from helper_get_names import FieldSqlErrorType  # type: ignore
from helper_get_names import (
    KEYSEPARATOR,
    HelperGetNames,
    InternalHelper,
    TableFieldType,
)

SOURCE = (Path(__file__).parent / ".." / ".." / "models.yml").resolve()
DESTINATION = (Path(__file__).parent / ".." / "sql" / "schema_relational.sql").resolve()
MODELS: dict[str, dict[str, Any]] = {}


class SchemaZoneTexts(TypedDict, total=False):
    """TypedDict definition for generation of different sql-code parts"""

    table: str
    view: str
    post_view: str
    alter_table: str
    alter_table_final: str
    create_trigger_relationlistnotnull: str
    create_trigger_notify: str
    undecided: str
    final_info: str
    errors: list[str]


class SQL_Delete_Update_Options(str, Enum):
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


class SubstDict(TypedDict, total=False):
    """dict for substitutions of field templates"""

    field_name: str
    type: str
    primary_key: str
    required: str
    default: str
    minimum: str
    minLength: str
    deferred: str
    check_enum: str


class GenerateCodeBlocks:
    """Main work is done here by recursing the models and their fields and determine the method to use"""

    intermediate_tables: dict[str, str] = (
        {}
    )  # Key=Name, data: collected content of table

    @classmethod
    def generate_the_code(
        cls,
    ) -> tuple[str, str, str, str, str, list[str], str, str, str, list[str]]:
        """
        Return values:
          pre_code: Type definitions etc., which should all appear before first table definitions
          table_name_code: All table definitions
          view_name_code: All view definitions, after all views, because of view field definition by sql
          alter_table_final_code: Changes on tables defining relations after, which should appear after all table/views definition to be sequence independant
          final_info_code: Detailed info about all relation fields.Types: relation, relation-list, generic-relation and generic-relation-list
          missing_handled_atributes: List of unhandled attributes. handled one's are to be set manually.
          im_table_code: Code for intermediate tables.
              n:m-relations name schema: f"nm_{smaller-table-name}_{it's-fieldname}_{greater-table_name}" uses one per relation
              g:m-relations name schema: f"gm_{table_field.table}_{table_field.column}" of table with generic-list-field
          create_trigger_relationlistnotnull_code: Definitions of triggers calling check_not_null_for_relation_lists
          create_trigger_notify_code: Definitions of triggers calling notify_modified_models
          errors: to show
        """
        handled_attributes = {
            "required",
            "maxLength",
            "minLength",
            "default",
            "type",
            "restriction_mode",
            "minimum",
            "calculated",
            "description",
            "read_only",
            "enum",
            "items",
            "to",
            "reference",
            # "on_delete", # must have other name then the key-value-store one
            # "sql"
            # "equal_fields", # Seems we need, see example_transactional.sql between meeting and groups?
            # "unique",  # TODO: still to design
        }
        pre_code: str = ""
        table_name_code: str = ""
        view_name_code: str = ""
        alter_table_final_code: str = ""
        create_trigger_relationlistnotnull_code: str = ""
        create_trigger_notify_code: str = ""
        final_info_code: str = ""
        missing_handled_attributes = []
        im_table_code = ""
        errors: list[str] = []

        for table_name, fields in MODELS.items():
            if table_name in ["_migration_index", "_meta"]:
                continue
            schema_zone_texts = cast(SchemaZoneTexts, defaultdict(str))
            cls.intermediate_tables = {}

            for fname, fdata in fields.items():
                for attr in fdata:
                    if (
                        attr not in handled_attributes
                        and attr not in missing_handled_attributes
                    ):
                        missing_handled_attributes.append(attr)
                method_or_str, type_ = cls.get_method(fname, fdata)
                if isinstance(method_or_str, str):
                    error = Helper.prefix_error(method_or_str, table_name, fname)
                    schema_zone_texts["undecided"] += error
                    errors.append(error)
                else:
                    result, error = method_or_str(table_name, fname, fdata, type_)
                    for k, v in result.items():
                        schema_zone_texts[k] += v or ""  # type: ignore
                    if error:
                        errors.append(Helper.prefix_error(error, table_name, fname))

            if code := schema_zone_texts["table"]:
                table_name_code += Helper.get_table_head(table_name)
                table_name_code += Helper.get_table_body_end(code) + "\n\n"
            if code := schema_zone_texts["alter_table"]:
                table_name_code += code + "\n"
            if code := schema_zone_texts["undecided"]:
                table_name_code += Helper.get_undecided_all(table_name, code)
            view_name_code += Helper.get_view_head(table_name)
            view_name_code += Helper.get_view_body_end(
                table_name, schema_zone_texts.get("view", "")
            )
            if code := schema_zone_texts["post_view"]:
                view_name_code += code
            if code := schema_zone_texts["alter_table_final"]:
                alter_table_final_code += code + "\n"
            if code := schema_zone_texts["create_trigger_relationlistnotnull"]:
                create_trigger_relationlistnotnull_code += code + "\n"
            if code := schema_zone_texts["final_info"]:
                final_info_code += code + "\n"
            for im_table in cls.intermediate_tables.values():
                im_table_code += im_table

            # schema_zone_texts is filled per model field.
            # If any fields for this collection generated table code, create the main notify trigger on it.
            if schema_zone_texts["table"]:
                create_trigger_notify_code += (
                    Helper.get_notify_trigger(table_name) + "\n"
                )
            # Special triggers (e.g. for relation fields) come after
            # TODO: needs to be filled in the get_*_relation_*_type functions
            if code := schema_zone_texts["create_trigger_notify"]:
                create_trigger_notify_code += code + "\n"

        return (
            pre_code,
            table_name_code,
            view_name_code,
            alter_table_final_code,
            final_info_code,
            missing_handled_attributes,
            im_table_code,
            create_trigger_relationlistnotnull_code,
            create_trigger_notify_code,
            errors,
        )

    @classmethod
    def get_method(
        cls, fname: str, fdata: dict[str, Any]
    ) -> tuple[str | Callable[..., tuple[SchemaZoneTexts, str]], str]:
        """
        returns
        - string or a callable with return value of type SchemaZoneTexts
        - type as string
        """
        if fdata.get("calculated"):
            return (
                f"type:{fdata.get('type')} is marked as a calculated field and not generated in schema\n",
                "",
            )
        if fname == "id":
            type_ = "primary_key"
        elif (
            fname == "organization_id"
        ):  # temporary, just to fill the 4 organization_id-fields automatically with 1
            type_ = "organization_id"
        else:
            type_ = fdata.get("type", "")
        if type_ in FIELD_TYPES:
            if method := FIELD_TYPES[type_].get("method"):
                return (method.__get__(cls), type_)  # returns the callable classmethod
            else:
                text = "no method defined"
        else:
            text = "Unknown Type"
        return (f"type:{type_} {text}\n", type_)

    @classmethod
    def get_schema_simple_types(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        subst, szt = Helper.get_initials(table_name, fname, type_, fdata)
        text.update(szt)
        if isinstance((tmp := subst["type"]), string.Template):
            if maxLength := fdata.get("maxLength"):
                tmp = tmp.substitute({"maxLength": maxLength})
            elif isinstance(type_, Decimal):
                tmp = tmp.substitute({"maxLength": 6})
            elif isinstance(type_, str):  # string
                tmp = tmp.substitute({"maxLength": 256})
            subst["type"] = tmp
        text["table"] = Helper.FIELD_TEMPLATE.substitute(subst)
        return text, ""

    @classmethod
    def get_schema_color(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        subst, szt = Helper.get_initials(table_name, fname, type_, fdata)
        text.update(szt)
        tmpl = FIELD_TYPES[type_]["pg_type"]
        subst["type"] = tmpl.substitute({"field_name": fname})
        text["table"] = Helper.FIELD_TEMPLATE.substitute(subst)
        return text, ""

    @classmethod
    def get_schema_primary_key(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        subst, tmp = Helper.get_initials(table_name, fname, type_, fdata)
        text.update(tmp)
        subst["primary_key"] = " PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY"
        text["table"] = Helper.FIELD_TEMPLATE.substitute(subst)
        return text, ""

    @classmethod
    def get_schema_organization_id(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        subst, tmp = Helper.get_initials(table_name, fname, type_, fdata)
        text.update(tmp)
        subst["primary_key"] = " GENERATED ALWAYS AS (1) STORED"
        text["table"] = Helper.FIELD_TEMPLATE.substitute(subst)
        return text, ""

    @classmethod
    def get_relation_type(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        own_table_field = TableFieldType(table_name, fname, fdata)
        foreign_table_field: TableFieldType = (
            TableFieldType.get_definitions_from_foreign(
                fdata.get("to"), fdata.get("reference")
            )
        )
        state, _, final_info, error = InternalHelper.check_relation_definitions(
            own_table_field, [foreign_table_field]
        )

        if state == FieldSqlErrorType.FIELD:
            text, error = cls.get_schema_simple_types(
                table_name, fname, fdata, "number"
            )
            initially_deferred = fdata.get(
                "deferred"
            ) or ModelsHelper.is_fk_initially_deferred(
                table_name, foreign_table_field.table
            )
            text["alter_table_final"] = (
                Helper.get_foreign_key_table_constraint_as_alter_table(
                    table_name,
                    foreign_table_field.table,
                    fname,
                    foreign_table_field.ref_column,
                    initially_deferred,
                )
            )
        elif state == FieldSqlErrorType.SQL:
            if sql := fdata.get("sql", ""):
                text["view"] = sql + ",\n"
            elif foreign_table_field.field_def["type"] == "generic-relation":
                text["view"] = cls.get_sql_for_relation_1_1(
                    table_name,
                    fname,
                    foreign_table_field.ref_column,
                    foreign_table_field.table,
                    f"{foreign_table_field.column}_{own_table_field.table}_{own_table_field.ref_column}",
                )
            else:
                text["view"] = cls.get_sql_for_relation_1_1(
                    table_name,
                    fname,
                    foreign_table_field.ref_column,
                    foreign_table_field.table,
                    cast(str, foreign_table_field.column),
                )
        text["final_info"] = final_info
        return text, error

    @classmethod
    def get_sql_for_relation_1_1(
        cls,
        table_name: str,
        fname: str,
        ref_column: str,
        foreign_table: str,
        foreign_column: str,
    ) -> str:
        table_letter = Helper.get_table_letter(table_name)
        letters = [table_letter]
        foreign_letter = Helper.get_table_letter(foreign_table, letters)
        foreign_table = HelperGetNames.get_table_name(foreign_table)
        return f"(select {foreign_letter}.{ref_column} from {foreign_table} {foreign_letter} where {foreign_letter}.{foreign_column} = {table_letter}.{ref_column}) as {fname},\n"

    @classmethod
    def get_relation_list_type(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        own_table_field = TableFieldType(table_name, fname, fdata)
        foreign_table_field: TableFieldType = (
            TableFieldType.get_definitions_from_foreign(
                fdata.get("to"),
                fdata.get("reference"),
            )
        )
        state, primary, final_info, error = InternalHelper.check_relation_definitions(
            own_table_field, [foreign_table_field]
        )

        if state != FieldSqlErrorType.ERROR:
            if primary:
                if foreign_table_field.field_def.get("type") == "relation-list":
                    nm_table_name, value = Helper.get_nm_table_for_n_m_relation_lists(
                        own_table_field, foreign_table_field
                    )
                    if nm_table_name not in cls.intermediate_tables:
                        cls.intermediate_tables[nm_table_name] = value
                    else:
                        raise Exception(
                            f"Tried to create im_table '{nm_table_name}' twice"
                        )
            if sql := fdata.get("sql", ""):
                text["view"] = sql + ",\n"
            else:
                foreign_table_column = cast(str, foreign_table_field.column)
                foreign_table_field_ref_id = cast(str, foreign_table_field.ref_column)
                if foreign_table_column or foreign_table_field_ref_id:
                    if (
                        type_ := foreign_table_field.field_def.get("type", "")
                    ) == "generic-relation":
                        own_ref_column = own_table_field.ref_column
                        foreign_table_column += (
                            f"_{table_name}_{foreign_table_field.ref_column}"
                        )
                        foreign_table_name = HelperGetNames.get_table_name(
                            foreign_table_field.table
                        )
                        foreign_table_ref_column = foreign_table_field.ref_column
                    elif type_ == "relation-list":
                        if own_table_field.table == foreign_table_field.table:
                            """Example: committee.forward_to_committee_ids to committee.receive_forwardings_from_committee_ids"""
                            own_ref_column = own_table_field.ref_column
                            foreign_table_ref_column = fname[:-1]
                            foreign_table_name = HelperGetNames.get_nm_table_name(
                                own_table_field, foreign_table_field
                            )
                            foreign_table_column = (
                                foreign_table_field.intermediate_column
                            )
                        else:
                            own_ref_column = own_table_field.ref_column
                            foreign_table_ref_column = f"{foreign_table_field.table}_{foreign_table_field.ref_column}"
                            foreign_table_name = HelperGetNames.get_nm_table_name(
                                own_table_field, foreign_table_field
                            )
                            foreign_table_column = (
                                f"{own_table_field.table}_{own_table_field.ref_column}"
                            )
                    elif type_ == "generic-relation-list":
                        own_ref_column = own_table_field.ref_column
                        foreign_table_ref_column = f"{foreign_table_field.table}_{foreign_table_field.ref_column}"
                        foreign_table_name = HelperGetNames.get_gm_table_name(
                            foreign_table_field
                        )
                        foreign_table_column = (
                            f"{foreign_table_field.intermediate_column}_{table_name}_id"
                        )
                    elif type_ == "relation" or foreign_table_field_ref_id:
                        own_ref_column = own_table_field.ref_column
                        foreign_table_ref_column = foreign_table_field.ref_column
                        foreign_table_name = HelperGetNames.get_table_name(
                            foreign_table_field.table
                        )
                        foreign_table_column = foreign_table_field.column
                    else:
                        raise Exception(
                            f"Still not implemented for foreign_table type '{type_}' in False case"
                        )
                text["view"] = cls.get_sql_for_relation_n_1(
                    table_name,
                    fname,
                    own_ref_column,
                    foreign_table_name,
                    foreign_table_column,
                    foreign_table_ref_column,
                    own_table_field.field_def == foreign_table_field.field_def,
                )
                if comment := fdata.get("description"):
                    text["post_view"] = Helper.get_post_view_comment(
                        HelperGetNames.get_view_name(table_name), fname, comment
                    )
                if own_table_field.field_def.get("required"):
                    text["create_trigger_relationlistnotnull"] = (
                        cls.get_trigger_check_not_null_for_relation_lists(
                            own_table_field.table,
                            own_table_field.column,
                            foreign_table_field.table,
                            foreign_table_field.column,
                        )
                    )
        text["final_info"] = final_info
        return text, error

    @classmethod
    def get_sql_for_relation_n_1(
        cls,
        table_name: str,
        fname: str,
        own_ref_column: str,
        foreign_table_name: str,
        foreign_table_column: str,
        foreign_table_ref_column: str,
        self_reference: bool = False,
    ) -> str:
        table_letter = Helper.get_table_letter(table_name)
        foreign_letter = Helper.get_table_letter(foreign_table_name, [table_letter])
        AGG_TEMPLATE = f"select array_agg({foreign_letter}.{{}}) from {foreign_table_name} {foreign_letter}"
        COND_TEMPLATE = (
            f" where {foreign_letter}.{{}} = {table_letter}.{own_ref_column}"
        )
        if not foreign_table_column or not self_reference:
            query = AGG_TEMPLATE.format(foreign_table_ref_column)
            if foreign_table_column:
                query += COND_TEMPLATE.format(foreign_table_column)
        else:
            assert foreign_table_ref_column == (col := foreign_table_column)
            arr1 = AGG_TEMPLATE.format(f"{col}_1") + COND_TEMPLATE.format(f"{col}_2")
            arr2 = AGG_TEMPLATE.format(f"{col}_2") + COND_TEMPLATE.format(f"{col}_1")
            query = f"select array_cat(({arr1}), ({arr2}))"
        return f"({query}) as {fname},\n"

    @classmethod
    def get_trigger_check_not_null_for_relation_lists(
        cls, own_table: str, own_column: str, foreign_table: str, foreign_column: str
    ) -> str:
        foreign_table_t = HelperGetNames.get_table_name(foreign_table)
        return dedent(
            f"""
            -- definition trigger not null for {own_table}.{own_column} against {foreign_table_t}.{foreign_column}
            CREATE CONSTRAINT TRIGGER {HelperGetNames.get_not_null_rel_list_insert_trigger_name(own_table, own_column)} AFTER INSERT ON {foreign_table_t} INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION check_not_null_for_relation_lists('{own_table}', '{own_column}', '{foreign_column}');

            CREATE CONSTRAINT TRIGGER {HelperGetNames.get_not_null_rel_list_upd_del_trigger_name(own_table, own_column)} AFTER UPDATE OF {foreign_column} OR DELETE ON {foreign_table_t}
            FOR EACH ROW EXECUTE FUNCTION check_not_null_for_relation_lists('{own_table}', '{own_column}', '{foreign_column}');

            """
        )

    @classmethod
    def get_generic_relation_type(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        own_table_field = TableFieldType(table_name, fname, fdata)
        foreign_table_fields: list[TableFieldType] = (
            InternalHelper.get_definitions_from_foreign_list(
                fdata.get("to"), fdata.get("reference")
            )
        )

        state, _, final_info, error = InternalHelper.check_relation_definitions(
            own_table_field, foreign_table_fields
        )

        if state == FieldSqlErrorType.FIELD:
            text, error = cls.get_schema_simple_types(
                table_name, fname, fdata, fdata["type"]
            )
            initially_deferred = any(
                ModelsHelper.is_fk_initially_deferred(
                    table_name, foreign_table_field.table
                )
                for foreign_table_field in foreign_table_fields
            )
            foreign_tables: list[str] = []
            for foreign_table_field in foreign_table_fields:
                generic_plain_field_name = f"{own_table_field.column}_{foreign_table_field.table}_{foreign_table_field.ref_column}"
                foreign_tables.append(foreign_table_field.table)
                text["table"] += Helper.get_generic_combined_fields(
                    generic_plain_field_name,
                    own_table_field.column,
                    foreign_table_field.table,
                )
                text[
                    "alter_table_final"
                ] += Helper.get_foreign_key_table_constraint_as_alter_table(
                    own_table_field.table,
                    foreign_table_field.table,
                    generic_plain_field_name,
                    foreign_table_field.ref_column,
                    initially_deferred,
                )
            text["table"] += Helper.get_generic_field_constraint(
                own_table_field.column, foreign_tables
            )
        text["final_info"] = final_info
        return text, error

    @classmethod
    def get_generic_relation_list_type(
        cls, table_name: str, fname: str, fdata: dict[str, Any], type_: str
    ) -> tuple[SchemaZoneTexts, str]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        own_table_field = TableFieldType(table_name, fname, fdata)
        foreign_table_fields: list[TableFieldType] = (
            InternalHelper.get_definitions_from_foreign_list(
                fdata.get("to"), fdata.get("reference")
            )
        )
        state, primary, final_info, error = InternalHelper.check_relation_definitions(
            own_table_field, foreign_table_fields
        )

        if state == FieldSqlErrorType.SQL and primary:
            # create gm-intermediate table
            if primary:
                gm_foreign_table, value = Helper.get_gm_table_for_gm_nm_relation_lists(
                    own_table_field, foreign_table_fields
                )
                if gm_foreign_table not in cls.intermediate_tables:
                    cls.intermediate_tables[gm_foreign_table] = value
                else:
                    raise Exception(
                        f"Tried to create gm_table '{gm_foreign_table}' twice"
                    )

            # add field to view definition of table_name
            text["view"] = cls.get_sql_for_relation_n_1(
                table_name,
                fname,
                own_table_field.ref_column,
                gm_foreign_table,
                f"{own_table_field.table}_{own_table_field.ref_column}",
                own_table_field.intermediate_column,
            )
            if comment := fdata.get("description"):
                text["post_view"] += Helper.get_post_view_comment(
                    HelperGetNames.get_view_name(table_name), fname, comment
                )

        text["final_info"] = final_info
        return text, error


class Helper:
    FILE_TEMPLATE_HEADER = dedent(
        """
        -- schema_relational.sql for initial database setup OpenSlides
        -- Code generated. DO NOT EDIT.
        """
    )
    FILE_TEMPLATE_PARAMETERS = dedent(
        """
        -- Do not log messages lower than WARNING
        -- For client side logging this can be overwritten using
        --
        -- SET client_min_messages TO NOTICE;
        --
        -- to get the log messages in the client locally.
        SET log_min_messages TO WARNING;
        """
    )
    FILE_TEMPLATE_CONSTANT_DEFINITIONS = dedent(
        """
        CREATE EXTENSION hstore;  -- included in standard postgres-installations, check for alpine

        CREATE FUNCTION check_not_null_for_relation_lists() RETURNS trigger as $not_null_trigger$
        -- usage with 3 parameters IN TRIGGER DEFINITION:
        -- table_name of field to check, usually a field in a view
        -- column_name of field to check
        -- foreign_key field name of triggered table, that will be used to SELECT the values to check the not null.
        DECLARE
            table_name TEXT;
            column_name TEXT;
            foreign_key TEXT;
            foreign_id INTEGER;
            counted INTEGER;
        begin
            table_name = TG_ARGV[0];
            column_name = TG_ARGV[1];
            foreign_key = TG_ARGV[2];

            IF (TG_OP = 'INSERT') THEN
                foreign_id := hstore(NEW) -> foreign_key;
                IF (foreign_id is NOT NULL) THEN
                    foreign_id = NULL; -- no need to ask DB
                END IF;
            ELSIF (TG_OP = 'UPDATE') THEN
                foreign_id := hstore(NEW) -> foreign_key;
                IF (foreign_id is NULL) THEN
                    foreign_id = OLD.used_as_default_projector_for_topic_in_meeting_id;
                END IF;
            ELSIF (TG_OP = 'DELETE') THEN
                foreign_id := hstore(OLD) -> foreign_key;
            END IF;

            IF (foreign_id IS NOT NULL) THEN
                EXECUTE format('SELECT array_length(%I, 1) FROM %I where id = %s', column_name, table_name, foreign_id) INTO counted;
                IF (counted is NULL) THEN
                    RAISE EXCEPTION 'Trigger % Exception: NOT NULL CONSTRAINT VIOLATED for %.%', TG_NAME, table_name, column_name;
                END IF;
            END IF;
            RETURN NULL;  -- AFTER TRIGGER needs no return
        end;
        $not_null_trigger$ language plpgsql;

        CREATE FUNCTION log_modified_models() RETURNS trigger AS $log_modified_trigger$
        DECLARE
            escaped_table_name varchar;
            operation TEXT;
            fqid TEXT;
        BEGIN
            escaped_table_name := TG_ARGV[0];
            operation := LOWER(TG_OP);
            fqid :=  escaped_table_name || '/' || NEW.id;
            IF (TG_OP = 'DELETE') THEN
                fqid = escaped_table_name || '/' || OLD.id;
            END IF;

            INSERT INTO os_notify_log_t (operation, fqid, xact_id, timestamp) VALUES (operation, fqid, pg_current_xact_id(), 'now');
            RETURN NULL;  -- AFTER TRIGGER needs no return
        END;
        $log_modified_trigger$ LANGUAGE plpgsql;

        CREATE FUNCTION notify_transaction_end() RETURNS trigger AS $notify_trigger$
        DECLARE
            payload TEXT;
            body_content_text TEXT;
        BEGIN
            -- Running the trigger for the first time in a transaction creates the table and after commiting the transaction the table is dropped.
            -- Every next run of the trigger in this transaction raises a notice that the table exists. Setting the log_min_messages to notice increases the noise because of such messages.
            CREATE LOCAL TEMPORARY TABLE
            IF NOT EXISTS tbl_notify_counter_tx_once (
                "id" integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY
            ) ON COMMIT DROP;

            -- If running for the first time, the transaction id is send via os_notify.
            IF NOT EXISTS (SELECT * FROM tbl_notify_counter_tx_once) THEN
                INSERT INTO tbl_notify_counter_tx_once DEFAULT VALUES;
                payload := '{"xactId":' ||
                    pg_current_xact_id() ||
                    '}';
                PERFORM pg_notify('os_notify', payload);
            END IF;

            RETURN NULL;  -- AFTER TRIGGER needs no return
        END;
        $notify_trigger$ LANGUAGE plpgsql;

        CREATE TABLE os_notify_log_t (
            id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            operation varchar(32),
            fqid varchar(256),
            xact_id xid8,
            timestamp timestamptz
        );
        """
    )
    FIELD_TEMPLATE = string.Template(
        "    ${field_name} ${type}${primary_key}${required}${check_enum}${minimum}${minLength}${default},\n"
    )
    INTERMEDIATE_TABLE_N_M_RELATION_TEMPLATE = string.Template(
        dedent(
            """
            CREATE TABLE ${table_name} (
                ${field1} integer NOT NULL REFERENCES ${table1} (id) ON DELETE CASCADE INITIALLY DEFERRED,
                ${field2} integer NOT NULL REFERENCES ${table2} (id) ON DELETE CASCADE INITIALLY DEFERRED,
                PRIMARY KEY (${list_of_keys})
            );
        """
        )
    )
    INTERMEDIATE_TABLE_G_M_RELATION_TEMPLATE = string.Template(
        dedent(
            """
            CREATE TABLE ${table_name} (
                id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                ${own_table_name_with_ref_column} integer NOT NULL REFERENCES ${own_table_name}(${own_table_ref_column}) ON DELETE CASCADE INITIALLY DEFERRED,
                ${own_table_column} varchar(100) NOT NULL,
            ${foreign_table_ref_lines}
                CONSTRAINT ${valid_constraint_name} CHECK (split_part(${own_table_column}, '/', 1) IN ${tuple_of_foreign_table_names}),
                CONSTRAINT ${unique_constraint_name} UNIQUE (${own_table_name_with_ref_column}, ${own_table_column})
            );
        """
        )
    )
    GM_FOREIGN_TABLE_LINE_TEMPLATE = string.Template(
        "    ${gm_content_field} integer GENERATED ALWAYS AS (CASE WHEN split_part(${own_table_column}, '/', 1) = '${foreign_view_name}' THEN cast(split_part(${own_table_column}, '/', 2) AS INTEGER) ELSE null END) STORED REFERENCES ${foreign_table_name}(id) ON DELETE CASCADE INITIALLY DEFERRED,"
    )

    RELATION_LIST_AGENDA = dedent(
        """
        /*   Relation-list infos
        Generated: What will be generated for left field
            FIELD: a usual Database field
            SQL: a sql-expression in a view
            ***: Error
        Field Attributes:Field Attributes opposite side
            1: cardinality 1
            1G: cardinality 1 with generic-relation field
            n: cardinality n
            nG: cardinality n with generic-relation-list field
            t: "to" defined
            r: "reference" defined
            s: sql directive inclusive sql-statement
            R: Required
        Model.Field -> Model.Field
            model.field names
        */

        """
    )

    @staticmethod
    def get_table_letter(table_name: str, letters: list[str] = []) -> str:
        letter = HelperGetNames.get_table_name(table_name)[0]
        count = -1
        start_letter = letter
        while True:
            if letter in letters:
                count += 1
                if count == 0:
                    start_letter = "".join([part[0] for part in table_name.split("_")])[
                        :2
                    ]
                    letter = start_letter
                else:
                    letter = start_letter + str(count)
            else:
                return letter

    @staticmethod
    def get_table_head(table_name: str) -> str:
        return f"\nCREATE TABLE {HelperGetNames.get_table_name(table_name)} (\n"

    @staticmethod
    def get_table_body_end(code: str) -> str:
        code = code[:-2] + "\n"  # last attribute line without ",", but with "\n"
        code += ");\n\n"
        return code

    @staticmethod
    def get_view_head(table_name: str) -> str:
        return f"\nCREATE VIEW {HelperGetNames.get_view_name(table_name)} AS SELECT *"

    @staticmethod
    def get_view_body_end(table_name: str, code: str) -> str:
        # change the code only if there is
        if code:
            # comma and "\n" for the header
            # last attribute line without ",", but with "\n"
            code = ",\n" + code[:-2] + "\n"
        else:
            code = " "
        code += f"FROM {HelperGetNames.get_table_name(table_name)} {Helper.get_table_letter(table_name)};\n\n"
        return code

    @staticmethod
    def get_notify_trigger(table_name: str) -> str:
        own_table = HelperGetNames.get_table_name(table_name)
        escaped_table_name = "'" + table_name + "'"
        code = f"CREATE TRIGGER log_modified_model AFTER INSERT OR UPDATE OR DELETE ON {own_table}\n"
        code += f"FOR EACH ROW EXECUTE FUNCTION log_modified_models({escaped_table_name});\n"
        code += f"CREATE CONSTRAINT TRIGGER notify_transaction_end AFTER INSERT OR UPDATE OR DELETE ON {own_table}\n"
        code += "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION notify_transaction_end();\n"
        return code

    @staticmethod
    def get_alter_table_final_code(code: str) -> str:
        return f"-- Alter table final relation commands\n{code}\n\n"

    @staticmethod
    def get_undecided_all(table_name: str, code: str) -> str:
        return (
            f"/*\n Fields without SQL definition for table {table_name}\n\n{code}\n*/\n"
        )

    @staticmethod
    def get_check_enum(
        table_name: str, fname: str, enum_: list[Any], type_: str
    ) -> str:
        check_enum_constraint_name = HelperGetNames.get_check_enum_constraint_name(
            table_name, fname
        )
        if type_.startswith("number"):
            enumeration = ", ".join([str(item) for item in enum_])
        elif type_.startswith("string"):
            enumeration = ", ".join([f"'{item}'" for item in enum_])
        else:
            raise Exception(f"enum for type {type_} not implemented")
        if type_.endswith("[]"):
            condition = f"{fname} <@ ARRAY[{enumeration}]::varchar[]"
        else:
            condition = f"{fname} IN ({enumeration})"
        return f" CONSTRAINT {check_enum_constraint_name} CHECK ({condition})"

    @staticmethod
    def get_foreign_key_table_constraint_as_alter_table(
        table_name: str,
        foreign_table: str,
        own_columns: list[str] | str,
        fk_columns: list[str] | str,
        initially_deferred: bool = False,
        delete_action: str = "",
        update_action: str = "",
    ) -> str:
        FOREIGN_KEY_TABLE_CONSTRAINT_TEMPLATE = string.Template(
            "ALTER TABLE ${own_table} ADD FOREIGN KEY(${own_columns}) REFERENCES ${foreign_table}(${fk_columns})${initially_deferred}"
        )

        if initially_deferred:
            text_initially_deferred = " INITIALLY DEFERRED"
        else:
            text_initially_deferred = ""
        if isinstance(own_columns, list):
            own_columns = "(" + ", ".join(own_columns) + ")"
        if isinstance(fk_columns, list):
            fk_columns = "(" + ", ".join(fk_columns) + ")"
        own_table = HelperGetNames.get_table_name(table_name)
        foreign_table = HelperGetNames.get_table_name(foreign_table)
        result = FOREIGN_KEY_TABLE_CONSTRAINT_TEMPLATE.substitute(
            {
                "own_table": own_table,
                "foreign_table": foreign_table,
                "own_columns": own_columns,
                "fk_columns": fk_columns,
                "initially_deferred": text_initially_deferred,
            }
        )
        result += Helper.get_on_action_mode(delete_action, True)
        result += Helper.get_on_action_mode(update_action, False)
        result += ";\n"
        return result

    @staticmethod
    def get_on_action_mode(action: str, delete: bool) -> str:
        if action:
            if (actionUpper := action.upper()) in SQL_Delete_Update_Options:
                return f" ON {'DELETE' if delete else 'UPDATE'} {SQL_Delete_Update_Options(actionUpper)}"
            else:
                raise Exception(f"{action} is not a valid action mode")
        return ""

    @staticmethod
    def get_nm_table_for_n_m_relation_lists(
        own_table_field: TableFieldType, foreign_table_field: TableFieldType
    ) -> tuple[str, str]:
        nm_table_name = HelperGetNames.get_nm_table_name(
            own_table_field, foreign_table_field
        )
        field1 = HelperGetNames.get_field_in_n_m_relation_list(
            own_table_field, foreign_table_field.table
        )
        field2 = HelperGetNames.get_field_in_n_m_relation_list(
            foreign_table_field, own_table_field.table
        )
        if field1 == field2:
            field1 += "_1"
            field2 += "_2"
        text = Helper.INTERMEDIATE_TABLE_N_M_RELATION_TEMPLATE.substitute(
            {
                "table_name": nm_table_name,  # without tailing _t
                "field1": field1,
                "table1": HelperGetNames.get_table_name(own_table_field.table),
                "field2": field2,
                "table2": HelperGetNames.get_table_name(foreign_table_field.table),
                "list_of_keys": ", ".join([field1, field2]),
            }
        )
        return nm_table_name, text

    @staticmethod
    def get_gm_table_for_gm_nm_relation_lists(
        own_table_field: TableFieldType, foreign_table_fields: list[TableFieldType]
    ) -> tuple[str, str]:
        gm_table_name = HelperGetNames.get_gm_table_name(own_table_field)
        joined_table_names = (
            "('"
            + "', '".join(
                [
                    foreign_table_field.table
                    for foreign_table_field in foreign_table_fields
                ]
            )
            + "')"
        )
        foreign_table_ref_lines = []
        own_table_column = own_table_field.intermediate_column
        for foreign_table_field in foreign_table_fields:
            foreign_table_name = foreign_table_field.table
            subst_dict = {
                "own_table_column": own_table_column,
                "foreign_table_name": HelperGetNames.get_table_name(foreign_table_name),
                "foreign_view_name": foreign_table_name,
                "gm_content_field": HelperGetNames.get_gm_content_field(
                    own_table_column, foreign_table_name
                ),
            }
            foreign_table_ref_lines.append(
                Helper.GM_FOREIGN_TABLE_LINE_TEMPLATE.substitute(subst_dict)
            )

        text = Helper.INTERMEDIATE_TABLE_G_M_RELATION_TEMPLATE.substitute(
            {
                "table_name": gm_table_name,  # without trailing _t
                "own_table_name": HelperGetNames.get_table_name(own_table_field.table),
                "own_table_name_with_ref_column": (
                    own_table_name_with_ref_column := f"{own_table_field.table}_{own_table_field.ref_column}"
                ),
                "own_table_ref_column": own_table_field.ref_column,
                "own_table_column": own_table_column,
                "tuple_of_foreign_table_names": joined_table_names,
                "foreign_table_ref_lines": "\n".join(foreign_table_ref_lines),
                "valid_constraint_name": HelperGetNames.get_generic_valid_constraint_name(
                    own_table_column
                ),
                "unique_constraint_name": HelperGetNames.get_generic_unique_constraint_name(
                    own_table_name_with_ref_column, own_table_column
                ),
            }
        )
        return gm_table_name, text

    @staticmethod
    def get_initials(
        table_name: str, fname: str, type_: str, fdata: dict[str, Any]
    ) -> tuple[SubstDict, SchemaZoneTexts]:
        text = cast(SchemaZoneTexts, defaultdict(str))
        flist: list[str] = [
            cast(str, form[1])
            for form in Formatter().parse(Helper.FIELD_TEMPLATE.template)
        ]
        subst: SubstDict = cast(SubstDict, {k: "" for k in flist})
        subst_type = FIELD_TYPES[type_]["pg_type"]
        subst.update({"field_name": fname, "type": subst_type})
        if fdata.get("required"):
            subst["required"] = " NOT NULL"
        if (default := fdata.get("default")) is not None:
            if isinstance(default, str) or type_ in ("string", "text"):
                subst["default"] = f" DEFAULT '{default}'"
            elif isinstance(default, (int, bool, float)):
                subst["default"] = f" DEFAULT {default}"
            elif isinstance(default, list):
                tmp = '{"' + '", "'.join(default) + '"}' if default else "{}"
                subst["default"] = f" DEFAULT '{tmp}'"
            else:
                raise Exception(
                    f"{table_name}.{fname}: seems to be an invalid default value"
                )
        if (enum_ := fdata.get("enum")) or (
            enum_ := fdata.get("items", {}).get("enum")
        ):
            subst["check_enum"] = Helper.get_check_enum(table_name, fname, enum_, type_)
        if (minimum := fdata.get("minimum")) is not None:
            minimum_constraint_name = HelperGetNames.get_minimum_constraint_name(fname)
            subst["minimum"] = (
                f" CONSTRAINT {minimum_constraint_name} CHECK ({fname} >= {minimum})"
            )
        if minLength := fdata.get("minLength"):
            minlength_constraint_name = HelperGetNames.get_minlength_constraint_name(
                fname
            )
            subst["minLength"] = (
                f" CONSTRAINT {minlength_constraint_name} CHECK (char_length({fname}) >= {minLength})"
            )
        if comment := fdata.get("description"):
            text["alter_table"] = Helper.get_post_view_comment(
                HelperGetNames.get_table_name(table_name), fname, comment
            )
        return subst, text

    @staticmethod
    def get_post_view_comment(entity_name: str, fname: str, comment: str) -> str:
        return f"comment on column {entity_name}.{fname} is '{comment}';\n"

    @staticmethod
    def get_generic_combined_fields(
        generic_plain_field_name: str, own_column: str, foreign_table: str
    ) -> str:
        return f"    {generic_plain_field_name} integer GENERATED ALWAYS AS (CASE WHEN split_part({own_column}, '/', 1) = '{foreign_table}' THEN cast(split_part({own_column}, '/', 2) AS INTEGER) ELSE null END) STORED,\n"

    @staticmethod
    def get_generic_field_constraint(own_column: str, foreign_tables: list[str]) -> str:
        constraint_name = HelperGetNames.get_generic_valid_constraint_name(own_column)
        return f"""    CONSTRAINT {constraint_name} CHECK (split_part({own_column}, '/', 1) IN ('{"','".join(foreign_tables)}')),\n"""

    @staticmethod
    def prefix_error(method_or_str: str, table_name: str, fname: str) -> str:
        return f"    {table_name}/{fname}: {method_or_str}"


class ModelsHelper:
    @staticmethod
    def is_fk_initially_deferred(own_table: str, foreign_table: str) -> bool:
        """
        The "Initially deferred" in fk-definition is necessary,
        if 2 related tables require both the relation to the other table
        """

        def _first_to_second(t1: str, t2: str) -> bool:
            for field in MODELS[t1].values():
                if field.get("required") and field["type"].startswith("relation"):
                    ftable = ModelsHelper.get_foreign_table_from_to_or_reference(
                        field.get("to"), field.get("reference")
                    )
                    if ftable == t2:
                        return True
            return False

        return True
        # TODO: Will be reverted in a future issue
        # if _first_to_second(own_table, foreign_table):
        #     return _first_to_second(foreign_table, own_table)
        # return False

    @staticmethod
    def get_foreign_table_from_to_or_reference(
        to: str | None, reference: str | None
    ) -> str:
        if reference:
            result = InternalHelper.ref_compiled.search(reference)
            if result is None:
                return reference.strip()
            re_groups = result.groups()
            return re_groups[0]
        elif to:
            return to.split(KEYSEPARATOR)[0]
        else:
            raise Exception("Relation field without reference or to")


FIELD_TYPES: dict[str, dict[str, Any]] = {
    "string": {
        "pg_type": string.Template("varchar(${maxLength})"),
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "number": {
        "pg_type": "integer",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "boolean": {
        "pg_type": "boolean",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "JSON": {"pg_type": "jsonb", "method": GenerateCodeBlocks.get_schema_simple_types},
    "HTMLStrict": {
        "pg_type": "text",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "HTMLPermissive": {
        "pg_type": "text",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "float": {"pg_type": "real", "method": GenerateCodeBlocks.get_schema_simple_types},
    "decimal(6)": {
        "pg_type": "decimal(16,6)",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "timestamp": {
        "pg_type": "timestamptz",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "color": {
        "pg_type": string.Template(
            "varchar(7) CHECK (${field_name} is null or ${field_name} ~* '^#[a-f0-9]{6}$$')"
        ),
        "method": GenerateCodeBlocks.get_schema_color,
    },
    "string[]": {
        "pg_type": string.Template("varchar(${maxLength})[]"),
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "number[]": {
        "pg_type": "integer[]",
        "method": GenerateCodeBlocks.get_schema_simple_types,
    },
    "text": {"pg_type": "text", "method": GenerateCodeBlocks.get_schema_simple_types},
    "relation": {"pg_type": "integer", "method": GenerateCodeBlocks.get_relation_type},
    "relation-list": {
        "pg_type": "integer[]",
        "method": GenerateCodeBlocks.get_relation_list_type,
    },
    "generic-relation": {
        "pg_type": "varchar(100)",
        "method": GenerateCodeBlocks.get_generic_relation_type,
    },
    "generic-relation-list": {
        "pg_type": "varchar(100)[]",
        "method": GenerateCodeBlocks.get_generic_relation_list_type,
    },
    # special defined
    "primary_key": {
        "pg_type": "integer",
        "method": GenerateCodeBlocks.get_schema_primary_key,
    },
    "organization_id": {
        "pg_type": "integer",
        "method": GenerateCodeBlocks.get_schema_organization_id,
    },
}


def main() -> None:
    """
    Main entry point for this script to generate the schema_relational.sql from models.yml.
    """

    global MODELS

    # Retrieve models.yml from call-parameter for testing purposes, local file or GitHub
    if len(sys.argv) > 1:
        file = sys.argv[1]
    else:
        file = str(SOURCE)

    MODELS, checksum = InternalHelper.read_models_yml(file)

    (
        pre_code,
        table_name_code,
        view_name_code,
        alter_table_code,
        final_info_code,
        missing_handled_attributes,
        im_table_code,
        create_trigger_relationlistnotnull_code,
        create_trigger_notify_code,
        errors,
    ) = GenerateCodeBlocks.generate_the_code()
    with open(DESTINATION, "w") as dest:
        dest.write(Helper.FILE_TEMPLATE_HEADER)
        dest.write("-- MODELS_YML_CHECKSUM = " + repr(checksum) + "\n")
        dest.write("\n\n-- Database parameters\n")
        dest.write(Helper.FILE_TEMPLATE_PARAMETERS)
        dest.write("\n\n-- Function and meta table definitions\n")
        dest.write(Helper.FILE_TEMPLATE_CONSTANT_DEFINITIONS)
        dest.write("\n\n-- Type definitions\n")
        dest.write(pre_code)
        dest.write("\n\n-- Table definitions\n")
        dest.write(table_name_code)
        dest.write("\n\n-- Intermediate table definitions\n")
        dest.write(im_table_code)
        dest.write("\n\n-- View definitions\n")
        dest.write(view_name_code)
        dest.write("\n\n-- Alter table relations\n")
        dest.write(alter_table_code)
        dest.write(
            "\n\n-- Create triggers checking foreign_id not null for relation-lists\n"
        )
        dest.write(create_trigger_relationlistnotnull_code)
        dest.write("\n\n-- Create triggers for notify\n")
        dest.write(create_trigger_notify_code)
        dest.write(Helper.RELATION_LIST_AGENDA)
        dest.write("/*\n")
        dest.write(final_info_code)
        dest.write("*/\n")
        if errors:
            dest.write(f"/*\nThere are {len(errors)} errors/warnings\n")
            dest.write("".join(errors))
            dest.write("*/\n")
        dest.write(
            f"\n/*   Missing attribute handling for {', '.join(missing_handled_attributes)} */"
        )
    if errors:
        print(f"Models file {DESTINATION} created with {len(errors)} errors/warnings\n")
        print("".join(errors))
    else:
        print(f"Models file {DESTINATION} successfully created.")


if __name__ == "__main__":
    main()
