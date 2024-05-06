import os
from collections.abc import Callable
from unittest import TestCase

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from src.db_utils import DbUtils
from src.python_sql import Table

# ADMIN_USERNAME = "admin"
# ADMIN_PASSWORD = "admin"


class BaseTestCase(TestCase):
    temporary_template_db = "openslides_template"
    work_on_test_db = "openslides_test"
    db_connection: psycopg.Connection

    # id's of pre loaded rows, see method populate_database
    meeting1_id = 0
    theme1_id = 0
    organization_id = 0
    user1_id = 0
    committee1_id = 0
    groupM1_default_id = 0
    groupM1_admin_id = 0
    groupM1_staff_id = 0
    simple_workflowM1_id = 0
    complex_workflowM1_id = 0

    @classmethod
    def set_db_connection(
        cls,
        db_name: str,
        autocommit: bool = False,
        row_factory: Callable = psycopg.rows.dict_row,
    ) -> None:
        env = os.environ
        try:
            cls.db_connection = psycopg.connect(
                f"dbname='{db_name}' user='{env['DATABASE_USER']}' host='{env['DATABASE_HOST']}' password='{env['PGPASSWORD']}'",
                autocommit=autocommit,
                row_factory=row_factory,
            )
            cls.db_connection.isolation_level = psycopg.IsolationLevel.SERIALIZABLE
        except Exception as e:
            raise Exception(f"Cannot connect to postgres: {e.message}")

    @classmethod
    def setup_class(cls) -> None:
        env = os.environ
        cls.set_db_connection("postgres", True)
        with cls.db_connection:
            with cls.db_connection.cursor() as curs:
                curs.execute(
                    sql.SQL(
                        "DROP DATABASE IF EXISTS {temporary_template_db} (FORCE);"
                    ).format(
                        temporary_template_db=sql.Identifier(cls.temporary_template_db)
                    )
                )
                curs.execute(
                    sql.SQL(
                        "CREATE DATABASE {db_to_create} TEMPLATE {template_db};"
                    ).format(
                        db_to_create=sql.Identifier(cls.temporary_template_db),
                        template_db=sql.Identifier(env["DATABASE_NAME"]),
                    )
                )
        cls.set_db_connection(cls.temporary_template_db)
        with cls.db_connection:
            with cls.db_connection.cursor() as curs:
                curs.execute("CREATE EXTENSION pldbgapi;")  # Postgres debug extension
            cls.populate_database()

    @classmethod
    def teardown_class(cls) -> None:
        """remove last test db and drop the temporary template db"""
        cls.set_db_connection("postgres", True)
        with cls.db_connection:
            with cls.db_connection.cursor() as curs:
                curs.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} (FORCE);").format(
                        sql.Identifier(cls.work_on_test_db)
                    )
                )
                curs.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} (FORCE);").format(
                        sql.Identifier(cls.temporary_template_db)
                    )
                )

    def setUp(self) -> None:
        self.set_db_connection("postgres", autocommit=True)
        with self.db_connection:
            with self.db_connection.cursor() as curs:
                curs.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} (FORCE);").format(
                        sql.Identifier(self.work_on_test_db)
                    )
                )
                curs.execute(
                    sql.SQL(
                        "CREATE DATABASE {test_db} TEMPLATE {temporary_template_db};"
                    ).format(
                        test_db=sql.Identifier(self.work_on_test_db),
                        temporary_template_db=sql.Identifier(
                            self.temporary_template_db
                        ),
                    )
                )

        self.set_db_connection(self.work_on_test_db)

    @classmethod
    def populate_database(cls) -> None:
        """do something like setting initial_data.json"""
        theme_t = Table("theme_t")
        organization_t = Table("organization_t")
        user_t = Table("user_t")
        committee_t = Table("committee_t")

        with cls.db_connection.transaction():
            with cls.db_connection.cursor() as curs:
                cls.theme1_id = curs.execute(
                    *theme_t.insert(
                        columns=[
                            theme_t.name,
                            theme_t.accent_500,
                            theme_t.primary_500,
                            theme_t.warn_500,
                        ],
                        values=[["OpenSlides Blue", "#2196f3", "#317796", "#f06400"]],
                        returning=[theme_t.id],
                    )
                ).fetchone()["id"]
                data = [
                    {
                        "name": "Test Organization",
                        "legal_notice": '<a href="http://www.openslides.org">OpenSlides</a> is a free web based presentation and assembly system for visualizing and controlling agenda, motions and elections of an assembly.',
                        "login_text": "Good Morning!",
                        "default_language": "en",
                        "genders": ["male", "female", "diverse", "non-binary"],
                        "enable_electronic_voting": True,
                        "enable_chat": True,
                        "reset_password_verbose_errors": True,
                        "limit_of_meetings": 0,
                        "limit_of_users": 0,
                        "theme_id": cls.theme1_id,
                        "users_email_sender": "OpenSlides",
                        "users_email_subject": "OpenSlides access data",
                        "users_email_body": "Dear {name},\n\nthis is your personal OpenSlides login:\n\n{url}\nUsername: {username}\nPassword: {password}\n\n\nThis email was generated automatically.",
                        "url": "https://example.com",
                        "saml_enabled": False,
                        "saml_login_button_text": "SAML Login",
                        "saml_attr_mapping": Jsonb(
                            {
                                "saml_id": "username",
                                "title": "title",
                                "first_name": "firstName",
                                "last_name": "lastName",
                                "email": "email",
                                "gender": "gender",
                                "pronoun": "pronoun",
                                "is_active": "is_active",
                                "is_physical_person": "is_person",
                            }
                        ),
                    }
                ]
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    organization_t, data
                )
                cls.organization_id = curs.execute(
                    *organization_t.insert(
                        columns, values, returning=[organization_t.id]
                    )
                ).fetchone()["id"]
                data = [
                    {
                        "username": "admin",
                        "last_name": "Administrator",
                        "is_active": True,
                        "is_physical_person": True,
                        "password": "316af7b2ddc20ead599c38541fbe87e9a9e4e960d4017d6e59de188b41b2758flD5BVZAZ8jLy4nYW9iomHcnkXWkfk3PgBjeiTSxjGG7+fBjMBxsaS1vIiAMxYh+K38l0gDW4wcP+i8tgoc4UBg==",
                        "default_password": "admin",
                        "can_change_own_password": True,
                        "gender": "male",
                        "default_vote_weight": "1.000000",
                        "organization_management_level": "superadmin",
                    }
                ]
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    user_t, data
                )
                cls.user1_id = curs.execute(
                    *user_t.insert(columns, values, returning=[user_t.id])
                ).fetchone()["id"]
                cls.committee1_id = curs.execute(
                    *committee_t.insert(
                        columns=[committee_t.name, committee_t.description],
                        values=[["Default committee", "Add description here"]],
                        returning=[committee_t.id],
                    )
                ).fetchone()["id"]
                result_ids = cls.create_meeting(curs, committee_id=cls.committee1_id)
                cls.meeting1_id = result_ids["meeting_id"]
                cls.groupM1_default_id = result_ids["default_group_id"]
                cls.groupM1_admin_id = result_ids["admin_group_id"]
                cls.groupM1_staff_id = result_ids["staff_group_id"]
                cls.simple_workflowM1_id = result_ids["simple_workflow_id"]
                cls.complex_workflowM1_id = result_ids["complex_workflow_id"]
                curs.execute(
                    *committee_t.update(
                        columns=[committee_t.default_meeting_id],
                        values=[cls.committee1_id],
                    )
                )

    @classmethod
    def create_meeting(
        cls,
        curs: psycopg.Cursor,
        committee_id: int,
        meeting_id: int = 0,
    ) -> dict[str, int]:
        """
        Creates meeting with next availale id if not set or id set (lower ids can't be choosed afterwards)
        The committee_id must be given and the committee must exist. The meeting will not be set as default meeting of the committee
        3 groups with permissions (Default, Admin, Staff) were created
        2 projectors (Default projector, Secondary projector) were created
        2 workflows (simple, complex were created)
        Return Value dict of ids with keys
        - meeting_id
        - default_group_id, admin_group_id, staff_group_id
        - default_project_id, secondary_projector_id
        - simple_workflow_id, complex_workflow_id
        """
        group_t = Table("group_t")
        projector_t = Table("projector_t")
        motion_state_t = Table("motion_state_t")
        nm_motion_state_next_state_ids_motion_state_t = Table(
            "nm_motion_state_next_state_ids_motion_state_t"
        )
        motion_workflow_t = Table("motion_workflow_t")
        meeting_t = Table("meeting_t")

        result = {}
        if meeting_id:
            sequence_name = curs.execute(
                "select * from pg_get_serial_sequence('meeting_t', 'id');"
            ).fetchone()["pg_get_serial_sequence"]
            last_value = curs.execute(
                f"select last_value from {sequence_name};"
            ).fetchone()["last_value"]
            if last_value >= meeting_id:
                raise ValueError(
                    f"meeting_id {meeting_id} is not available, last_value in sequence {sequence_name} is {last_value}"
                )
            result["meeting_id"] = curs.execute(
                "select setval(pg_get_serial_sequence('meeting_t', 'id'), %s);",
                (meeting_id,),
            ).fetchone()["setval"]
        else:
            result["meeting_id"] = curs.execute(
                "select nextval(pg_get_serial_sequence('meeting_t', 'id')) as id_;"
            ).fetchone()["id_"]
        curs.execute(
            *group_t.insert(
                columns=[
                    group_t.name,
                    group_t.permissions,
                    group_t.weight,
                    group_t.meeting_id,
                ],
                values=[
                    [
                        "Default",
                        [
                            "agenda_item.can_see_internal",
                            "assignment.can_see",
                            "list_of_speakers.can_see",
                            "mediafile.can_see",
                            "meeting.can_see_frontpage",
                            "motion.can_see",
                            "projector.can_see",
                            "user.can_see",
                        ],
                        1,
                        result["meeting_id"],
                    ],
                    ["Admin", [], 2, result["meeting_id"]],
                    [
                        "Staff",
                        [
                            "agenda_item.can_manage",
                            "assignment.can_manage",
                            "assignment.can_nominate_self",
                            "list_of_speakers.can_be_speaker",
                            "list_of_speakers.can_manage",
                            "mediafile.can_manage",
                            "meeting.can_see_frontpage",
                            "meeting.can_see_history",
                            "motion.can_manage",
                            "poll.can_manage",
                            "projector.can_manage",
                            "tag.can_manage",
                            "user.can_manage",
                        ],
                        3,
                        result["meeting_id"],
                    ],
                ],
                returning=[group_t.id],
            )
        )
        (
            result["default_group_id"],
            result["admin_group_id"],
            result["staff_group_id"],
        ) = (x["id"] for x in curs)
        data = [
            {
                "name": "Default projector",
                "is_internal": False,
                "scale": 0,
                "scroll": 0,
                "width": 1220,
                "aspect_ratio_numerator": 4,
                "aspect_ratio_denominator": 3,
                "color": "#000000",
                "background_color": "#ffffff",
                "header_background_color": "#317796",
                "header_font_color": "#f5f5f5",
                "header_h1_color": "#317796",
                "chyron_background_color": "#317796",
                "chyron_font_color": "#ffffff",
                "show_header_footer": True,
                "show_title": True,
                "show_logo": True,
                "show_clock": True,
                "sequential_number": 1,
                "used_as_default_projector_for_agenda_item_list_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_topic_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_list_of_speakers_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_current_los_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_motion_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_amendment_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_motion_block_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_assignment_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_mediafile_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_message_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_countdown_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_assignment_poll_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_motion_poll_in_meeting_id": result[
                    "meeting_id"
                ],
                "used_as_default_projector_for_poll_in_meeting_id": result[
                    "meeting_id"
                ],
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "Secondary projector",
                "is_internal": False,
                "scale": 0,
                "scroll": 0,
                "width": 1024,
                "aspect_ratio_numerator": 16,
                "aspect_ratio_denominator": 9,
                "color": "#000000",
                "background_color": "#888888",
                "header_background_color": "#317796",
                "header_font_color": "#f5f5f5",
                "header_h1_color": "#317796",
                "chyron_background_color": "#317796",
                "chyron_font_color": "#ffffff",
                "show_header_footer": True,
                "show_title": True,
                "show_logo": True,
                "show_clock": True,
                "sequential_number": 2,
                "meeting_id": result["meeting_id"],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(projector_t, data)
        curs.execute(*projector_t.insert(columns, values, returning=[projector_t.id]))
        (result["default_projector_id"], result["secondary_projector_id"]) = (
            x["id"] for x in curs
        )

        result["simple_workflow_id"] = curs.execute(
            "select nextval(pg_get_serial_sequence('motion_workflow_t', 'id')) as new_id;"
        ).fetchone()["new_id"]
        result["complex_workflow_id"] = curs.execute(
            "select nextval(pg_get_serial_sequence('motion_workflow_t', 'id')) as new_id;"
        ).fetchone()["new_id"]
        motion_state_data = [
            {
                "name": "submitted",
                "weight": 1,
                "css_class": "lightblue",
                "allow_support": True,
                "allow_create_poll": True,
                "allow_submitter_edit": True,
                "set_number": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["simple_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "set_workflow_timestamp": True,
                "allow_motion_forwarding": True,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "accepted",
                "weight": 2,
                "recommendation_label": "Acceptance",
                "css_class": "green",
                "set_number": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["simple_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "set_workflow_timestamp": False,
                "allow_motion_forwarding": True,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "rejected",
                "weight": 3,
                "recommendation_label": "Rejection",
                "css_class": "red",
                "set_number": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["simple_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "not decided",
                "weight": 4,
                "recommendation_label": "No decision",
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["simple_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(
            motion_state_t, motion_state_data
        )
        curs.execute(
            *motion_state_t.insert(columns, values, returning=[motion_state_t.id])
        )
        wf_m1_simple_motion_state_ids = [x["id"] for x in curs]
        wf_m1_simple_first_state_id = wf_m1_simple_motion_state_ids[0]

        motion_state_data = [
            {
                "name": "in progress",
                "weight": 5,
                "css_class": "lightblue",
                "set_number": False,
                "allow_submitter_edit": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_create_poll": False,
                "allow_support": False,
                "set_workflow_timestamp": True,
                "allow_motion_forwarding": True,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "submitted",
                "weight": 6,
                "css_class": "lightblue",
                "set_number": False,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": True,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "permitted",
                "weight": 7,
                "recommendation_label": "Permission",
                "css_class": "lightblue",
                "set_number": True,
                "merge_amendment_into_final": "undefined",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": True,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": 1,
            },
            {
                "name": "accepted",
                "weight": 8,
                "recommendation_label": "Acceptance",
                "css_class": "green",
                "set_number": True,
                "merge_amendment_into_final": "do_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "rejected",
                "weight": 9,
                "recommendation_label": "Rejection",
                "css_class": "red",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "withdrawn",
                "weight": 10,
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "adjourned",
                "weight": 11,
                "recommendation_label": "Adjournment",
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "not concerned",
                "weight": 12,
                "recommendation_label": "No concernment",
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "referred to committee",
                "weight": 13,
                "recommendation_label": "Referral to committee",
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "needs review",
                "weight": 14,
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
            {
                "name": "rejected (not authorized)",
                "weight": 15,
                "recommendation_label": "Rejection (not authorized)",
                "css_class": "grey",
                "set_number": True,
                "merge_amendment_into_final": "do_not_merge",
                "workflow_id": result["complex_workflow_id"],
                "restrictions": [],
                "show_state_extension_field": False,
                "show_recommendation_extension_field": False,
                "allow_submitter_edit": False,
                "allow_create_poll": False,
                "allow_support": False,
                "allow_motion_forwarding": True,
                "set_workflow_timestamp": False,
                "meeting_id": result["meeting_id"],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(
            motion_state_t, motion_state_data
        )
        curs.execute(
            *motion_state_t.insert(columns, values, returning=[motion_state_t.id])
        )
        wf_m1_complex_motion_state_ids = [x["id"] for x in curs]
        wf_m1_complex_first_state_id = wf_m1_complex_motion_state_ids[0]

        data = [
            {
                "next_state_id": wf_m1_simple_motion_state_ids[1],
                "previous_state_id": wf_m1_simple_motion_state_ids[0],
            },
            {
                "next_state_id": wf_m1_simple_motion_state_ids[2],
                "previous_state_id": wf_m1_simple_motion_state_ids[0],
            },
            {
                "next_state_id": wf_m1_simple_motion_state_ids[3],
                "previous_state_id": wf_m1_simple_motion_state_ids[0],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[1],
                "previous_state_id": wf_m1_complex_motion_state_ids[0],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[5],
                "previous_state_id": wf_m1_complex_motion_state_ids[0],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[2],
                "previous_state_id": wf_m1_complex_motion_state_ids[1],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[5],
                "previous_state_id": wf_m1_complex_motion_state_ids[1],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[10],
                "previous_state_id": wf_m1_complex_motion_state_ids[1],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[3],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[4],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[5],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[6],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[7],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[8],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
            {
                "next_state_id": wf_m1_complex_motion_state_ids[9],
                "previous_state_id": wf_m1_complex_motion_state_ids[2],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(
            nm_motion_state_next_state_ids_motion_state_t, data
        )
        curs.execute(
            *nm_motion_state_next_state_ids_motion_state_t.insert(columns, values)
        )

        data = [
            {
                "id": result["simple_workflow_id"],
                "name": "Simple Workflow",
                "sequential_number": 1,
                "first_state_id": wf_m1_simple_first_state_id,
                "meeting_id": result["meeting_id"],
            },
            {
                "id": result["complex_workflow_id"],
                "name": "Complex Workflow",
                "sequential_number": 2,
                "first_state_id": wf_m1_complex_first_state_id,
                "meeting_id": result["meeting_id"],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(
            motion_workflow_t, data
        )
        curs.execute(
            *motion_workflow_t.insert(columns, values, returning=[motion_workflow_t.id])
        )
        assert [
            result["simple_workflow_id"],
            result["complex_workflow_id"],
        ] == [x["id"] for x in curs]

        data = [
            {
                "id": result["meeting_id"],
                "name": "OpenSlides Demo",
                "is_active_in_organization_id": cls.organization_id,
                "language": "en",
                "conference_los_restriction": True,
                "agenda_number_prefix": "TOP",
                "motions_default_workflow_id": result["simple_workflow_id"],
                "motions_default_amendment_workflow_id": result["complex_workflow_id"],
                "motions_default_statute_amendment_workflow_id": result[
                    "complex_workflow_id"
                ],
                "motions_recommendations_by": "ABK",
                "motions_statute_recommendations_by": "",
                "motions_statutes_enabled": True,
                "motions_amendments_of_amendments": True,
                "motions_amendments_prefix": "-\u00c4",
                "motions_supporters_min_amount": 1,
                "motions_export_preamble": "",
                "users_enable_presence_view": True,
                "users_pdf_wlan_encryption": "",
                "users_enable_vote_delegations": True,
                "poll_ballot_paper_selection": "CUSTOM_NUMBER",
                "poll_ballot_paper_number": 8,
                "poll_sort_poll_result_by_votes": True,
                "poll_default_type": "nominal",
                "poll_default_method": "votes",
                "poll_default_onehundred_percent_base": "valid",
                "committee_id": committee_id,
                "reference_projector_id": result["default_projector_id"],
                "default_group_id": result["default_group_id"],
                "admin_group_id": result["admin_group_id"],
            },
        ]
        columns, values = DbUtils.get_columns_and_values_for_insert(meeting_t, data)
        assert (
            result["meeting_id"]
            == curs.execute(
                *meeting_t.insert(columns, values, returning=[meeting_t.id])
            ).fetchone()["id"]
        )
        return result