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
