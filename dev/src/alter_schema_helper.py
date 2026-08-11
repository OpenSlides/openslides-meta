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
    def get_alter_view_part(view_name: str) -> str:
        return f"ALTER VIEW {view_name}"

    @staticmethod
    def get_alter_table_part(table_name: str) -> str:
        return f"ALTER TABLE {table_name}"

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
