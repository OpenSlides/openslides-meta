import string

from .generate_schema_helper import Helper
from .helper_get_names import HelperGetNames


class AlterSchemaHelper:
    @staticmethod
    def get_foreign_key_table_constraint_as_alter_table(
        table_name: str,
        foreign_table: str,
        own_column: str,
        fk_column: str,
        initially_deferred: bool = False,
        delete_action: str = "",
        update_action: str = "",
    ) -> str:
        FOREIGN_KEY_TABLE_CONSTRAINT_TEMPLATE = string.Template(
            "ALTER TABLE ${own_table} ADD CONSTRAINT ${fk_name} FOREIGN KEY(${own_column}) REFERENCES ${foreign_table}(${fk_column})${initially_deferred}${delete_action}${update_action};\n"
            "CREATE INDEX ${index} ON ${own_table} (${own_column});\n"
        )

        if initially_deferred:
            text_initially_deferred = " INITIALLY DEFERRED"
        else:
            text_initially_deferred = ""
        own_table = HelperGetNames.get_table_name(table_name)
        foreign_table = HelperGetNames.get_table_name(foreign_table)
        fk_idx = HelperGetNames.get_fk_and_index_name(
            own_table, own_column, foreign_table, fk_column
        )
        result = FOREIGN_KEY_TABLE_CONSTRAINT_TEMPLATE.substitute(
            {
                "own_table": own_table,
                "fk_name": fk_idx[0],
                "index": fk_idx[1],
                "foreign_table": foreign_table,
                "own_column": own_column,
                "fk_column": fk_column,
                "initially_deferred": text_initially_deferred,
                "delete_action": Helper.get_on_action_mode(delete_action, True),
                "update_action": Helper.get_on_action_mode(update_action, False),
            }
        )
        return result

    @staticmethod
    def get_rename_part(what: str, new: str) -> str:
        return f"RENAME{what} TO {new}"

    @staticmethod
    def get_rename_column_part(column_name_old: str, column_name_new: str) -> str:
        return AlterSchemaHelper.get_rename_part(
            f" COLUMN {column_name_old}", column_name_new
        )

    @staticmethod
    def get_rename_constraint_part(
        constraint_name_old: str, constraint_name_new: str
    ) -> str:
        return AlterSchemaHelper.get_rename_part(
            f" CONSTRAINT {constraint_name_old}", constraint_name_new
        )

    @staticmethod
    def get_alter_view_part(view_name: str) -> str:
        return f"ALTER VIEW {view_name}"

    @staticmethod
    def get_alter_table_part(table_name: str) -> str:
        return f"ALTER TABLE {table_name}"

    @staticmethod
    def get_alter_type_part(type_name: str) -> str:
        return f"ALTER TYPE {type_name}"

    @staticmethod
    def get_rename_view_column(
        view_name: str, column_name_old: str, column_name_new: str
    ) -> str:
        avp = AlterSchemaHelper.get_alter_view_part(view_name)
        rcp = AlterSchemaHelper.get_rename_column_part(column_name_old, column_name_new)
        return f"{avp} {rcp};\n"

    @staticmethod
    def get_rename_table_column(
        table_name: str, column_name_old: str, column_name_new: str
    ) -> str:
        atp = AlterSchemaHelper.get_alter_table_part(table_name)
        rcp = AlterSchemaHelper.get_rename_column_part(column_name_old, column_name_new)
        return f"{atp} {rcp};\n"

    @staticmethod
    def get_rename_view(view_name_old: str, view_name_new: str) -> str:
        avp = AlterSchemaHelper.get_alter_view_part(view_name_old)
        rp = AlterSchemaHelper.get_rename_part("", view_name_new)
        return f"{avp} {rp};\n"

    @staticmethod
    def get_rename_table(table_name_old: str, table_name_new: str) -> str:
        atp = AlterSchemaHelper.get_alter_table_part(table_name_old)
        rp = AlterSchemaHelper.get_rename_part("", table_name_new)
        return f"{atp} {rp};\n"

    @staticmethod
    def get_rename_enum(enum_name_old: str, enum_name_new: str) -> str:
        atp = AlterSchemaHelper.get_alter_type_part(enum_name_old)
        rp = AlterSchemaHelper.get_rename_part("", enum_name_new)
        return f"{atp} {rp};\n"

    @staticmethod
    def get_rename_constraint(
        table_name: str, constraint_name_old: str, constraint_name_new: str
    ) -> str:
        atp = AlterSchemaHelper.get_alter_table_part(table_name)
        rcp = AlterSchemaHelper.get_rename_constraint_part(
            constraint_name_old, constraint_name_new
        )
        return f"{atp} {rcp};\n"

    @staticmethod
    def get_rename_index(idx_name_old: str, idx_name_new: str) -> str:
        rp = AlterSchemaHelper.get_rename_part("", idx_name_new)
        return f"ALTER INDEX {idx_name_old} {rp};\n"

    @staticmethod
    def get_rename_trigger(
        table_name: str, trigger_name_old: str, trigger_name_new: str
    ) -> str:
        rp = AlterSchemaHelper.get_rename_part("", trigger_name_new)
        return f"ALTER TRIGGER {trigger_name_old} ON {table_name} {rp};\n"

    @staticmethod
    def get_drop_type_statement(enum_name: str) -> str:
        return f"DROP TYPE {enum_name};\n"

    @staticmethod
    def get_drop_enum_type_statement_from_collection_and_column(
        collection_name: str, column_name: str
    ) -> str:
        return AlterSchemaHelper.get_drop_type_statement(
            HelperGetNames.get_enum_name_for_column(collection_name, column_name)
        )

    @staticmethod
    def get_drop_table_statement(collection_or_table_name: str) -> str:
        return f"DROP TABLE {HelperGetNames.get_table_name(collection_or_table_name)} CASCADE;\n"

    @staticmethod
    def get_alter_table_statement(collection_or_table_name: str, action: str) -> str:
        alter_table_part = AlterSchemaHelper.get_alter_table_part(
            HelperGetNames.get_table_name(collection_or_table_name)
        )
        return f"{alter_table_part} {action};\n"

    @staticmethod
    def get_drop_column_statement(
        collection_or_table_name: str, column_name: str
    ) -> str:
        return AlterSchemaHelper.get_alter_table_statement(
            collection_or_table_name, f"DROP COLUMN {column_name} CASCADE"
        )

    @staticmethod
    def get_drop_index_statement(collection_or_table_name: str, index: str) -> str:
        return AlterSchemaHelper.get_alter_table_statement(
            collection_or_table_name, f"DROP INDEX {index}"
        )

    @staticmethod
    def get_alter_column_statement(
        collection_or_table_name: str, column_name: str, action: str
    ) -> str:
        return AlterSchemaHelper.get_alter_table_statement(
            collection_or_table_name, f"ALTER COLUMN {column_name} {action}"
        )

    @staticmethod
    def get_drop_column_attribute_statement(
        collection_or_table_name: str, column_name: str, attribute: str
    ) -> str:
        return AlterSchemaHelper.get_alter_column_statement(
            collection_or_table_name, column_name, f"DROP {attribute}"
        )

    @staticmethod
    def get_drop_table_constraint_statement(
        collection_or_table_name: str, constraint_name: str
    ) -> str:
        return AlterSchemaHelper.get_alter_table_statement(
            collection_or_table_name, f"DROP CONSTRAINT {constraint_name}"
        )

    @staticmethod
    def get_drop_trigger_statement(
        collection_or_table_name: str, trigger_name: str
    ) -> str:
        return f"DROP TRIGGER {trigger_name} ON {HelperGetNames.get_table_name(collection_or_table_name)};\n"
