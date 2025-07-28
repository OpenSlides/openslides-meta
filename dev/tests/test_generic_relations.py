from typing import Any

import psycopg
import pytest
from psycopg import sql

from src.db_utils import DbUtils
from src.python_sql import Table
from tests.base import BaseTestCase

agenda_item_t = Table("agenda_item_t")
assignment_t = Table("assignment_t")
assignment_v = Table("assignment")
committee_v = Table("committee")
gm_organization_tag_tagged_ids_t = Table("gm_organization_tag_tagged_ids_t")
group_v = Table("group_")
group_t = Table("group_t")
list_of_speakers_t = Table("list_of_speakers_t")
list_of_speakers_v = Table("list_of_speakers")
mediafile_t = Table("mediafile_t")
mediafile_v = Table("mediafile")
meeting_t = Table("meeting_t")
meeting_v = Table("meeting")
option_t = Table("option_t")
organization_tag_t = Table("organization_tag_t")
organization_v = Table("organization")
poll_candidate_list_t = Table("poll_candidate_list_t")
poll_candidate_list_v = Table("poll_candidate_list")
projector_t = Table("projector")
theme_v = Table("theme")
user_v = Table("user_")


class Relations(BaseTestCase):
    """
    Used symbols in names of test:
    1: cardinality 1
    1G: cardinality 1 with generic-relation field
    n: cardinality n
    nG: cardinality n with generic-relation-list field
    t: "to" defined
    r: "reference" defined
    s: sql directive given, but must be generated
    s+: sql directive inclusive sql-statement
    R: Required
    """

    """ 1:n relation tests with n-side NOT NULL """
    """ Test:motion_state.submitter_withdraw_back_ids: sql okay?"""
    """ 1:1 relation tests """

    # todo: 1Gr errors
    def test_generic_1Gr_check_constraint_error(self) -> None:
        """tries to use a not defined owner-model for generic field owner_id"""
        with pytest.raises(psycopg.DatabaseError) as e:
            with self.db_connection.cursor() as curs:
                with self.db_connection.transaction():
                    curs.execute(
                        *mediafile_t.insert(
                            [mediafile_t.is_public, mediafile_t.owner_id],
                            [[True, f"motion_state/{self.meeting1_id}"]],
                        )
                    )
        assert (
            'new row for relation "mediafile_t" violates check constraint "valid_owner_id_part1"'
            in str(e)
        )

    # todo: 1GrR errors
    # todo: 1r errors
    # todo: 1rR errors

    # todo: 1t:1GrR
    def test_o2o_generic_1t_1GrR_okay(self) -> None:
        """SQL 1t:1GrR => assignment/agenda_item_id:-> agenda_item/content_object_id"""
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                assignment_id = curs.execute(
                    *assignment_t.insert(
                        [
                            assignment_t.title,
                            assignment_t.sequential_number,
                            assignment_t.meeting_id,
                        ],
                        [["title assignment 1", 21, self.meeting1_id]],
                        returning=[assignment_t.id],
                    )
                ).fetchone()["id"]
                assignment = f"assignment/{assignment_id}"
                agenda_item_id = curs.execute(
                    *agenda_item_t.insert(
                        [
                            agenda_item_t.item_number,
                            agenda_item_t.content_object_id,
                            agenda_item_t.meeting_id,
                        ],
                        [["100", assignment, self.meeting1_id]],
                        returning=[agenda_item_t.id],
                    )
                ).fetchone()["id"]
            assignment_row = curs.execute(
                *assignment_v.select(
                    where=assignment_v.agenda_item_id == agenda_item_id
                )
            ).fetchone()
            agenda_item_row = curs.execute(
                *agenda_item_t.select(
                    where=agenda_item_t.content_object_id == assignment
                )
            ).fetchone()
        assert assignment_row["agenda_item_id"] == agenda_item_row["id"]
        assert agenda_item_row["content_object_id"] == assignment
        assert (
            agenda_item_row["content_object_id_assignment_id"] == 1
        )  # internal storage

    def test_o2o_generic_1t_1GrR_okay_with_setval(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                mediafile_id = 2
                los_id = 3
                curs.execute(
                    "select setval(pg_get_serial_sequence('mediafile_t', 'id'), %s);",
                    (mediafile_id,),
                )
                assert (
                    mediafile_id
                    == curs.execute(
                        *mediafile_t.insert(
                            [
                                mediafile_t.id,
                                mediafile_t.is_public,
                                mediafile_t.owner_id,
                            ],
                            [[mediafile_id, True, f"meeting/{self.meeting1_id}"]],
                            returning=[mediafile_t.id],
                        )
                    ).fetchone()["id"]
                )
                curs.execute(
                    "select setval(pg_get_serial_sequence('list_of_speakers_t', 'id'), %s);",
                    (los_id,),
                )
                data = [
                    {
                        "id": los_id,
                        "content_object_id": (
                            content_object_id := f"mediafile/{mediafile_id}"
                        ),
                        "meeting_id": self.meeting1_id,
                        "sequential_number": 28,
                    },
                ]
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    list_of_speakers_t, data
                )
                assert (
                    los_id
                    == curs.execute(
                        *list_of_speakers_t.insert(
                            columns, values, returning=[list_of_speakers_t.id]
                        )
                    ).fetchone()["id"]
                )
            los_row: dict[str, Any] = curs.execute(
                *list_of_speakers_t.select(
                    list_of_speakers_t.id,
                    list_of_speakers_t.content_object_id,
                    list_of_speakers_t.content_object_id_mediafile_id,
                    list_of_speakers_t.content_object_id_topic_id,
                    where=list_of_speakers_t.id == los_id,
                )
            ).fetchone()
            assert los_row["id"] == los_id
            assert los_row["content_object_id"] == content_object_id
            assert los_row["content_object_id_mediafile_id"] == mediafile_id
            assert los_row["content_object_id_topic_id"] is None

            mediafile_row = curs.execute(
                *mediafile_v.select(
                    mediafile_v.id,
                    mediafile_v.list_of_speakers_id,
                    mediafile_v.owner_id,
                    where=mediafile_v.id == mediafile_id,
                )
            ).fetchone()
            assert mediafile_row["id"] == mediafile_id
            assert mediafile_row["list_of_speakers_id"] == los_id

    # todo: 1t:1r
    def test_o2o_pre_populated_1t_1r_okay(self) -> None:
        with self.db_connection.cursor() as curs:
            committee_row = curs.execute(
                *committee_v.select(
                    committee_v.default_meeting_id,
                    where=committee_v.id == self.committee1_id,
                )
            ).fetchone()
            assert committee_row["default_meeting_id"] == self.meeting1_id
            meeting_row = curs.execute(
                *meeting_v.select(
                    meeting_v.default_meeting_for_committee_id,
                    where=meeting_v.id == self.meeting1_id,
                )
            ).fetchone()
            assert meeting_row["default_meeting_for_committee_id"] == self.committee1_id

    # todo: 1t:1rR
    def test_o2o_pre_populated_1t_1rR_okay(self) -> None:
        with self.db_connection.cursor() as curs:
            organization_row = curs.execute(
                *organization_v.select(
                    organization_v.theme_id,
                    where=organization_v.id == self.organization_id,
                )
            ).fetchone()
            assert organization_row["theme_id"] == self.theme1_id
            theme_row = curs.execute(
                *theme_v.select(
                    theme_v.theme_for_organization_id,
                    where=theme_v.id == self.theme1_id,
                )
            ).fetchone()
            assert theme_row["theme_for_organization_id"] == self.organization_id

    def test_o2o_1t_1rR_okay_with_change_data(self) -> None:
        with self.db_connection.cursor() as curs:
            # Prepopulated
            meeting_row = curs.execute(
                *meeting_v.select(
                    meeting_v.default_group_id, where=meeting_v.id == self.meeting1_id
                )
            ).fetchone()
            old_default_group_id = meeting_row["default_group_id"]
            old_default_group_row = curs.execute(
                *group_v.select(
                    group_v.default_group_for_meeting_id,
                    where=group_v.id == old_default_group_id,
                )
            ).fetchone()
            assert (
                old_default_group_row["default_group_for_meeting_id"]
                == self.meeting1_id
            )
            # change default group
            with self.db_connection.transaction():
                group_staff_row = curs.execute(
                    *group_v.select(
                        group_v.id,
                        group_v.name,
                        group_v.meeting_id,
                        group_v.default_group_for_meeting_id,
                        where=(
                            (group_v.name == "Staff")
                            & (group_v.meeting_id == self.meeting1_id)
                        ),
                    )
                ).fetchone()
                assert group_staff_row["id"] == self.groupM1_staff_id
                assert group_staff_row["name"] == "Staff"
                assert group_staff_row["meeting_id"] == self.meeting1_id
                assert group_staff_row["default_group_for_meeting_id"] is None
                curs.execute(
                    *meeting_t.update(
                        [meeting_t.default_group_id],
                        [group_staff_row["id"]],
                        where=meeting_t.id == self.meeting1_id,
                    )
                )

            # assert new and old data
            meeting_row = curs.execute(
                *meeting_v.select(
                    meeting_v.default_group_id, where=meeting_v.id == self.meeting1_id
                )
            ).fetchone()
            assert meeting_row["default_group_id"] == group_staff_row["id"]
            new_default_group_row = curs.execute(
                *group_v.select(
                    group_v.default_group_for_meeting_id,
                    where=group_v.id == group_staff_row["id"],
                )
            ).fetchone()
            assert (
                new_default_group_row["default_group_for_meeting_id"]
                == self.meeting1_id
            )
            old_default_group_row = curs.execute(
                *group_v.select(
                    group_v.default_group_for_meeting_id,
                    where=group_v.id == old_default_group_id,
                )
            ).fetchone()
            assert old_default_group_row["default_group_for_meeting_id"] is None

    # todo: 1tR:1Gr
    def test_o2o_generic_1tR_1Gr_okay_with_setval(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                pcl_id = 2
                option_id = 3
                curs.execute(
                    "select setval(pg_get_serial_sequence('poll_candidate_list_t', 'id'), %s);",
                    (pcl_id,),
                )
                assert (
                    pcl_id
                    == curs.execute(
                        *poll_candidate_list_t.insert(
                            [
                                poll_candidate_list_t.id,
                                poll_candidate_list_t.meeting_id,
                            ],
                            [[pcl_id, self.meeting1_id]],
                            returning=[poll_candidate_list_t.id],
                        )
                    ).fetchone()["id"]
                )
                curs.execute(
                    "select setval(pg_get_serial_sequence('option_t', 'id'), %s);",
                    (option_id,),
                )
                data = [
                    {
                        "id": option_id,
                        "content_object_id": (
                            content_object_id := f"poll_candidate_list/{pcl_id}"
                        ),
                        "meeting_id": self.meeting1_id,
                    },
                ]
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    option_t, data
                )
                assert (
                    option_id
                    == curs.execute(
                        *option_t.insert(columns, values, returning=[option_t.id])
                    ).fetchone()["id"]
                )
            columns = DbUtils.get_columns_from_list(
                option_t,
                [
                    "id",
                    "content_object_id",
                    "content_object_id_poll_candidate_list_id",
                    "content_object_id_user_id",
                ],
            )
            option_row = curs.execute(
                *option_t.select(*columns, where=option_t.id == option_id)
            ).fetchone()
            assert option_row["id"] == option_id
            assert option_row["content_object_id"] == content_object_id
            assert option_row["content_object_id_poll_candidate_list_id"] == pcl_id
            assert option_row["content_object_id_user_id"] is None

            pcl_row = curs.execute(
                *poll_candidate_list_v.select(
                    poll_candidate_list_v.id,
                    poll_candidate_list_v.option_id,
                    where=poll_candidate_list_v.id == pcl_id,
                )
            ).fetchone()
            assert pcl_row["id"] == pcl_id
            assert pcl_row["option_id"] == option_id

    # todo: 1tR:1GrR to implement R:R
    def test_generic_1tR_1GrR_okay(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                assignment_id = 2
                los_id = 3
                curs.execute(
                    "select setval(pg_get_serial_sequence('assignment_t', 'id'), %s);",
                    (assignment_id,),
                )
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    assignment_t,
                    [
                        {
                            "id": assignment_id,
                            "title": "I am an assignment",
                            "sequential_number": 42,
                            "meeting_id": self.meeting1_id,
                        },
                    ],
                )
                assert (
                    assignment_id
                    == curs.execute(
                        *assignment_t.insert(
                            columns, values, returning=[assignment_t.id]
                        )
                    ).fetchone()["id"]
                )

                curs.execute(
                    "select setval(pg_get_serial_sequence('list_of_speakers_t', 'id'), %s);",
                    (los_id,),
                )
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    list_of_speakers_t,
                    [
                        {
                            "id": los_id,
                            "content_object_id": (
                                content_object_id := f"assignment/{assignment_id}"
                            ),
                            "meeting_id": self.meeting1_id,
                            "sequential_number": 28,
                        }
                    ],
                )
                assert (
                    los_id
                    == curs.execute(
                        *list_of_speakers_t.insert(
                            columns, values, returning=[list_of_speakers_t.id]
                        )
                    ).fetchone()["id"]
                )

            los_row = curs.execute(
                *list_of_speakers_v.select(
                    list_of_speakers_v.id,
                    list_of_speakers_v.content_object_id,
                    where=list_of_speakers_v.id == los_id,
                )
            ).fetchone()
            assert los_row["id"] == los_id
            assert los_row["content_object_id"] == content_object_id

            assignment_row = curs.execute(
                *assignment_v.select(
                    assignment_v.id,
                    assignment_v.list_of_speakers_id,
                    where=assignment_v.id == assignment_id,
                )
            ).fetchone()
            assert assignment_row["id"] == assignment_id
            assert assignment_row["list_of_speakers_id"] == los_id

    # todo: nGt:nt only error check nGt
    def test_generic_nGt_check_constraint_error(self) -> None:
        with pytest.raises(psycopg.DatabaseError) as e:
            with self.db_connection.cursor() as curs:
                with self.db_connection.transaction():
                    tag_id = curs.execute(
                        *organization_tag_t.insert(
                            [organization_tag_t.name, organization_tag_t.color],
                            [["Orga Tag 1", "#ffee13"]],
                            returning=[organization_tag_t.id],
                        )
                    ).fetchone()["id"]
                    columns, values = DbUtils.get_columns_and_values_for_insert(
                        gm_organization_tag_tagged_ids_t,
                        [
                            {
                                "organization_tag_id": tag_id,
                                "tagged_id": f"committee/{self.committee1_id}",
                            },
                            {
                                "organization_tag_id": tag_id,
                                "tagged_id": f"motion_state/{self.meeting1_id}",
                            },
                        ],
                    )
                    curs.execute(
                        *gm_organization_tag_tagged_ids_t.insert(columns, values)
                    )
        assert (
            'new row for relation "gm_organization_tag_tagged_ids_t" violates check constraint "valid_tagged_id_part1"'
            in str(e)
        )

    def test_generic_nGt_unique_constraint_error(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                tag_id = curs.execute(
                    *organization_tag_t.insert(
                        [organization_tag_t.name, organization_tag_t.color],
                        [["Orga Tag 1", "#ffee13"]],
                        returning=[organization_tag_t.id],
                    )
                ).fetchone()["id"]
                curs.execute(
                    *gm_organization_tag_tagged_ids_t.insert(
                        [
                            gm_organization_tag_tagged_ids_t.organization_tag_id,
                            gm_organization_tag_tagged_ids_t.tagged_id,
                        ],
                        [[tag_id, f"committee/{self.committee1_id}"]],
                        returning=[gm_organization_tag_tagged_ids_t.id],
                    )
                ).fetchone()["id"]
            with pytest.raises(psycopg.DatabaseError) as e:
                with self.db_connection.transaction():
                    curs.execute(
                        *gm_organization_tag_tagged_ids_t.insert(
                            [
                                gm_organization_tag_tagged_ids_t.organization_tag_id,
                                gm_organization_tag_tagged_ids_t.tagged_id,
                            ],
                            [[tag_id, f"committee/{self.committee1_id}"]],
                            returning=[gm_organization_tag_tagged_ids_t.id],
                        )
                    )
            assert "duplicate key value violates unique constraint" in str(e)

    # todo: nr
    # todo: nt:1Gr
    def test_generic_nt_1Gr(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                option_id = 3
                curs.execute(
                    "select setval(pg_get_serial_sequence('poll_candidate_list_t', 'id'), %s);",
                    (option_id,),
                )
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    option_t,
                    [
                        {
                            "id": option_id,
                            "content_object_id": (
                                content_object_id := f"user/{self.user1_id}"
                            ),
                            "meeting_id": self.meeting1_id,
                        },
                    ],
                )
                option_id = curs.execute(
                    *option_t.insert(columns, values, returning=[option_t.id])
                ).fetchone()["id"]
            option_row = curs.execute(
                *option_t.select(
                    *DbUtils.get_columns_from_list(
                        option_t,
                        [
                            "id",
                            "content_object_id",
                            "content_object_id_user_id",
                            "content_object_id_poll_candidate_list_id",
                        ],
                    ),
                    where=option_t.id == option_id,
                )
            ).fetchone()
            assert option_row["id"] == option_id
            assert option_row["content_object_id"] == content_object_id
            assert option_row["content_object_id_user_id"] == self.user1_id
            assert option_row["content_object_id_poll_candidate_list_id"] is None

            user_row = curs.execute(
                *user_v.select(
                    user_v.username, user_v.option_ids, where=user_v.id == self.user1_id
                )
            ).fetchone()
            assert user_row["option_ids"] == [option_id]
            assert user_row["username"] == "admin"

    # todo: nt:1GrR
    def test_o2m_generic_nt_1GrR_okay(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    mediafile_t,
                    [
                        {"is_public": True, "owner_id": f"meeting/{self.meeting1_id}"},
                        {
                            "is_public": True,
                            "owner_id": f"organization/{self.organization_id}",
                        },
                        {"is_public": True, "owner_id": f"meeting/{self.meeting1_id}"},
                        {
                            "is_public": True,
                            "owner_id": f"organization/{self.organization_id}",
                        },
                    ],
                )
                curs.execute(*mediafile_t.insert(columns, values))
            rows = curs.execute(
                *mediafile_v.select(
                    mediafile_v.owner_id,
                    mediafile_v.owner_id_meeting_id,
                    mediafile_v.owner_id_organization_id,
                )
            ).fetchall()
            expected_results = (
                ("meeting/1", 1, None),
                ("organization/1", None, 1),
                ("meeting/1", 1, None),
                ("organization/1", None, 1),
            )
            for i, row in enumerate(rows):
                assert tuple(row.values()) == expected_results[i]

            meeting_row = curs.execute(
                *meeting_v.select(
                    meeting_v.mediafile_ids, where=meeting_v.id == self.meeting1_id
                )
            ).fetchone()
            assert meeting_row["mediafile_ids"] == [1, 3]
            organization_row = curs.execute(
                *organization_v.select(organization_v.mediafile_ids)
            ).fetchone()
            assert organization_row["mediafile_ids"] == [2, 4]

    # todo: nt:1r
    # todo: nt:1rR
    # todo: nt:nGt
    def test_n2m_generic_nt_nGt_okay(self) -> None:
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    organization_tag_t,
                    [
                        {"name": "Orga Tag 1", "color": "#ffee13"},
                        {"name": "Orga Tag 2", "color": "#12ee13"},
                        {"name": "Orga Tag 3", "color": "#00ee13"},
                    ],
                )

                curs.execute(
                    *organization_tag_t.insert(
                        columns, values, returning=[organization_tag_t.id]
                    )
                )
                tag_ids = [x["id"] for x in curs]
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    gm_organization_tag_tagged_ids_t,
                    [
                        {
                            "organization_tag_id": tag_ids[0],
                            "tagged_id": f"committee/{self.committee1_id}",
                        },
                        {
                            "organization_tag_id": tag_ids[0],
                            "tagged_id": f"meeting/{self.meeting1_id}",
                        },
                        {
                            "organization_tag_id": tag_ids[1],
                            "tagged_id": f"committee/{self.committee1_id}",
                        },
                        {
                            "organization_tag_id": tag_ids[2],
                            "tagged_id": f"meeting/{self.meeting1_id}",
                        },
                    ],
                )
                curs.execute(*gm_organization_tag_tagged_ids_t.insert(columns, values))
            rows = curs.execute(
                *gm_organization_tag_tagged_ids_t.select(
                    *DbUtils.get_columns_from_list(
                        gm_organization_tag_tagged_ids_t,
                        [
                            "id",
                            "organization_tag_id",
                            "tagged_id",
                            "tagged_id_committee_id",
                            "tagged_id_meeting_id",
                        ],
                    )
                )
            ).fetchall()
            expected_results = (
                (1, 1, "committee/1", 1, None),
                (2, 1, "meeting/1", None, 1),
                (3, 2, "committee/1", 1, None),
                (4, 3, "meeting/1", None, 1),
            )
            for i, row in enumerate(rows):
                assert tuple(row.values()) == expected_results[i]

            committee_row = curs.execute(
                *committee_v.select(
                    committee_v.organization_tag_ids,
                    where=committee_v.id == self.committee1_id,
                )
            ).fetchone()
            assert committee_row["organization_tag_ids"] == [1, 2]
            meeting_row = curs.execute(
                *meeting_v.select(
                    meeting_v.organization_tag_ids,
                    where=meeting_v.id == self.meeting1_id,
                )
            ).fetchone()
            assert meeting_row["organization_tag_ids"] == [1, 3]

    # todo: nt:nt
    # todo: ntR:1r
    def test_o2m_ntR_1r_update_okay(self) -> None:
        """Update sets new default projector before 2nd removes old default projector"""
        with self.db_connection.cursor() as curs:
            projector_ids = curs.execute(
                *projector_t.select(
                    projector_t.id, where=projector_t.meeting_id == self.meeting1_id
                )
            ).fetchall()
            with self.db_connection.transaction():
                curs.execute(
                    *projector_t.update(
                        [projector_t.used_as_default_projector_for_topic_in_meeting_id],
                        [self.meeting1_id],
                        where=projector_t.id == [projector_ids[1]["id"]],
                    )
                )
                curs.execute(
                    *projector_t.update(
                        [projector_t.used_as_default_projector_for_topic_in_meeting_id],
                        [None],
                        where=projector_t.id == [projector_ids[0]["id"]],
                    )
                )
            assert (
                projector_ids[1]["id"]
                == curs.execute(
                    *meeting_v.select(
                        meeting_v.default_projector_topic_ids,
                        where=meeting_v.id == self.meeting1_id,
                    )
                ).fetchone()["default_projector_topic_ids"][0]
            )

    def test_o2m_ntR_1r_update_error(self) -> None:
        """update removes default projector => Exception"""
        with self.db_connection.cursor() as curs:
            with pytest.raises(psycopg.errors.RaiseException) as e:
                projector_id = curs.execute(
                    *projector_t.select(
                        projector_t.id,
                        where=projector_t.used_as_default_projector_for_topic_in_meeting_id
                        == self.meeting1_id,
                    )
                ).fetchone()["id"]
                with self.db_connection.transaction():
                    curs.execute(
                        *projector_t.update(
                            [
                                projector_t.used_as_default_projector_for_topic_in_meeting_id
                            ],
                            [
                                None,
                            ],
                            where=projector_t.id == projector_id,
                        )
                    )
        assert (
            "Exception: NOT NULL CONSTRAINT VIOLATED for meeting.default_projector_topic_ids"
            in str(e)
        )

    def test_o2m_ntR_1r_delete_error(self) -> None:
        """delete projector from meeting => Exception"""
        with self.db_connection.cursor() as curs:
            projector_id = curs.execute(
                "SELECT id from projector where used_as_default_projector_for_topic_in_meeting_id = %s",
                (self.meeting1_id,),
            ).fetchone()["id"]
            with pytest.raises(psycopg.errors.RaiseException) as e:
                with self.db_connection.transaction():
                    curs.execute(
                        sql.SQL("DELETE FROM projector where id = %s;"), (projector_id,)
                    )
        assert "Exception: NOT NULL CONSTRAINT VIOLATED" in str(e)

    def test_o2m_ntR_1r_insert_delete_okay(self) -> None:
        """first insert, than delete old default projector from meeting => okay"""
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                columns = DbUtils.get_columns_from_list(
                    projector_t,
                    [
                        "id",
                        "meeting_id",
                        "used_as_default_projector_for_agenda_item_list_in_meeting_id",
                        "used_as_default_projector_for_topic_in_meeting_id",
                        "used_as_default_projector_for_list_of_speakers_in_meeting_id",
                        "used_as_default_projector_for_current_los_in_meeting_id",
                        "used_as_default_projector_for_motion_in_meeting_id",
                        "used_as_default_projector_for_amendment_in_meeting_id",
                        "used_as_default_projector_for_motion_block_in_meeting_id",
                        "used_as_default_projector_for_assignment_in_meeting_id",
                        "used_as_default_projector_for_mediafile_in_meeting_id",
                        "used_as_default_projector_for_message_in_meeting_id",
                        "used_as_default_projector_for_countdown_in_meeting_id",
                        "used_as_default_projector_for_assignment_poll_in_meeting_id",
                        "used_as_default_projector_for_motion_poll_in_meeting_id",
                        "used_as_default_projector_for_poll_in_meeting_id",
                        "sequential_number",
                    ],
                )
                projector: dict[str, Any] = curs.execute(
                    *projector_t.select(
                        *columns,
                        where=projector_t.used_as_default_projector_for_topic_in_meeting_id
                        == self.meeting1_id,
                    )
                ).fetchone()
                projector_old_id = projector.pop("id")
                projector["sequential_number"] += 2
                columns, values = DbUtils.get_columns_and_values_for_insert(
                    projector_t, [projector]
                )
                projector_new_id = curs.execute(
                    *projector_t.insert(columns, values, returning=[projector_t.id])
                ).fetchone()["id"]
                curs.execute(
                    *meeting_t.update(
                        [meeting_t.reference_projector_id], [projector_new_id]
                    )
                )
                curs.execute(
                    *projector_t.delete(where=projector_t.id == projector_old_id)
                )
            assert (
                projector_new_id
                == curs.execute(
                    *meeting_v.select(
                        meeting_v.default_projector_topic_ids,
                        where=projector_new_id == meeting_v.reference_projector_id,
                    )
                ).fetchone()["default_projector_topic_ids"][0]
            )

    # todo: nts:nts


class EnumTests(BaseTestCase):
    def test_correct_singular_values_in_meeting(self) -> None:
        meeting_t = Table("meeting_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                meeting = curs.execute(
                    *meeting_t.select(
                        meeting_t.language,
                        meeting_t.export_pdf_fontsize,
                        where=meeting_t.id == 1,
                    )
                ).fetchone()
                assert meeting["language"] == "en"
                assert meeting["export_pdf_fontsize"] == 10
                meeting = curs.execute(
                    *meeting_t.update(
                        [meeting_t.language, meeting_t.export_pdf_fontsize],
                        ["de", 11],
                        where=meeting_t.id == 1,
                        returning=[meeting_t.id, meeting_t.language],
                    )
                ).fetchone()
        assert meeting["language"] == "de"

    def test_wrong_language_in_meeting(self) -> None:
        meeting_t = Table("meeting_t")
        with self.db_connection.cursor() as curs:
            with pytest.raises(psycopg.DatabaseError) as e:
                with self.db_connection.transaction():
                    curs.execute(
                        *meeting_t.update(
                            [meeting_t.language], ["xx"], where=meeting_t.id == 1
                        )
                    )
        assert 'violates check constraint "enum_meeting_language"' in str(e)

    def test_wrong_pdf_fontsize_in_meeting(self) -> None:
        meeting_t = Table("meeting_t")
        with self.db_connection.cursor() as curs:
            with pytest.raises(psycopg.DatabaseError) as e:
                with self.db_connection.transaction():
                    curs.execute(
                        *meeting_t.update(
                            [meeting_t.export_pdf_fontsize],
                            [22],
                            where=meeting_t.id == 1,
                        )
                    )
        assert 'violates check constraint "enum_meeting_export_pdf_fontsize"' in str(e)

    def test_correct_permissions_in_group(self) -> None:
        group_t = Table("group_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                group: dict[str, Any] = curs.execute(
                    *group_t.select(group_t.permissions, where=group_t.id == 1)
                ).fetchone()
                assert "agenda_item.can_see_internal" in group["permissions"]
                assert "user.can_see" in group["permissions"]
                assert "chat.can_manage" not in group["permissions"]
                group["permissions"].remove("user.can_see")
                group["permissions"].append("chat.can_manage")
                sql = tuple(
                    group_t.update(
                        [group_t.permissions],
                        [
                            DbUtils.get_pg_array_for_cu(group["permissions"]),
                        ],
                        where=group_t.id == 1,
                        returning=[group_t.permissions],
                    )
                )
                group = curs.execute(*sql).fetchone()
        assert "agenda_item.can_see_internal" in group["permissions"]
        assert "user.can_see" not in group["permissions"]
        assert "chat.can_manage" in group["permissions"]

    def test_wrong_permissions_in_group(self) -> None:
        group_t = Table("group_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                with pytest.raises(psycopg.DatabaseError) as e:
                    group = {"permissions": ["user.can_see", "invalid permission"]}
                    sql = tuple(
                        group_t.update(
                            [group_t.permissions],
                            [
                                DbUtils.get_pg_array_for_cu(group["permissions"]),
                            ],
                            where=group_t.id == 1,
                            returning=[group_t.permissions],
                        )
                    )
                    group = curs.execute(*sql).fetchone()
        assert 'violates check constraint "enum_group_permissions"' in str(e)


class DataTypeTests(BaseTestCase):
    def test_color_type_correct(self) -> None:
        orga_tag_t = Table("organization_tag_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                orga_tags = curs.execute(
                    *orga_tag_t.insert(
                        columns=[orga_tag_t.name, orga_tag_t.color],
                        values=[["Foo", "#ff12cc"], ["Bar", "#1234AA"]],
                        returning=[orga_tag_t.id, orga_tag_t.name, orga_tag_t.color],
                    )
                ).fetchall()
                assert orga_tags[0] == {"id": 1, "name": "Foo", "color": "#ff12cc"}
                assert orga_tags[1] == {"id": 2, "name": "Bar", "color": "#1234AA"}

    def test_color_type_not_null_error(self) -> None:
        orga_tag_t = Table("organization_tag_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                with pytest.raises(psycopg.DatabaseError) as e:
                    curs.execute(
                        *orga_tag_t.insert(
                            columns=[orga_tag_t.name, orga_tag_t.color],
                            values=[["Foo", None]],
                            returning=[
                                orga_tag_t.id,
                                orga_tag_t.name,
                                orga_tag_t.color,
                            ],
                        )
                    ).fetchone()
        assert (
            'null value in column "color" of relation "organization_tag_t" violates not-null constraint'
            in str(e)
        )

    def test_color_type_null_correct(self) -> None:
        sl_t = Table("structure_level_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                sl_id = curs.execute(
                    *sl_t.insert(
                        columns=[sl_t.name, sl_t.color, sl_t.meeting_id],
                        values=[["Foo", None, 1]],
                        returning=[sl_t.id],
                    )
                ).fetchone()["id"]
                structure_level = curs.execute(
                    *sl_t.select(sl_t.id, sl_t.color, where=sl_t.id == sl_id)
                ).fetchone()
                assert structure_level == {"id": sl_id, "color": None}

    def test_color_type_empty_string_error(self) -> None:
        sl_t = Table("structure_level_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                with pytest.raises(psycopg.DatabaseError) as e:
                    curs.execute(
                        *sl_t.insert(
                            columns=[sl_t.name, sl_t.color, sl_t.meeting_id],
                            values=[["Foo", "", 1]],
                            returning=[sl_t.id],
                        )
                    ).fetchone()["id"]
        assert (
            """new row for relation "structure_level_t" violates check constraint "structure_level_t_color_check"""
            in str(e)
        )

    def test_color_type_wrong_string_error(self) -> None:
        sl_t = Table("structure_level_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                with pytest.raises(psycopg.DatabaseError) as e:
                    curs.execute(
                        *sl_t.insert(
                            columns=[sl_t.name, sl_t.color, sl_t.meeting_id],
                            values=[["Foo", "xxx", 1]],
                            returning=[sl_t.id],
                        )
                    ).fetchone()["id"]
        assert (
            """new row for relation "structure_level_t" violates check constraint "structure_level_t_color_check"""
            in str(e)
        )

    def test_color_type_to_long_string_error(self) -> None:
        sl_t = Table("structure_level_t")
        with self.db_connection.cursor() as curs:
            with self.db_connection.transaction():
                with pytest.raises(psycopg.DatabaseError) as e:
                    curs.execute(
                        *sl_t.insert(
                            columns=[sl_t.name, sl_t.color, sl_t.meeting_id],
                            values=[["Foo", "#1234567", 1]],
                            returning=[sl_t.id],
                        )
                    ).fetchone()["id"]
        assert """value too long for type character varying(7)""" in str(e)


class ManualSqlTests(BaseTestCase):
    pass


class ConstraintTests(BaseTestCase):
    """foreign keys etc."""
