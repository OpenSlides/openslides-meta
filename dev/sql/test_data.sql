-- This script should only be used for an database filled with base_data.sql.

--relation --relation-list gender_ids
INSERT INTO user_t (username, gender_id) VALUES ('tom', 1);

BEGIN;

INSERT INTO motion_state_t (id, name, weight, workflow_id, meeting_id)
VALUES (5, 'motionState5', 1, 2, 2);
SELECT nextval('motion_state_t_id_seq');

INSERT INTO motion_workflow_t (
    id, name, first_state_id, meeting_id
)
VALUES (2, 'workflow2', 4, 2);
SELECT nextval('motion_workflow_t_id_seq');

INSERT INTO meeting_t (
    id,
    name,
    motions_default_workflow_id,
    motions_default_amendment_workflow_id,
    committee_id,
    reference_projector_id,
    default_group_id
)
VALUES (2, 'name', 2, 2, 2, 2, 3);
SELECT nextval('meeting_t_id_seq');


--generic-relation-list tagged_ids
INSERT INTO organization_tag_t (id, name, color)
VALUES (1, 'tagA', '#cc3b03');
SELECT nextval('organization_tag_t_id_seq');

--relation-list organization_tag_ids --relation 1:1 default_meeting_id
INSERT INTO committee_t (id, name, default_meeting_id)
VALUES (2, 'plenum', 2);
SELECT nextval('committee_t_id_seq');

INSERT INTO projector_t (
    id,
    meeting_id,
    used_as_default_projector_for_agenda_item_list_in_meeting_id,
    used_as_default_projector_for_topic_in_meeting_id,
    used_as_default_projector_for_list_of_speakers_in_meeting_id,
    used_as_default_projector_for_current_los_in_meeting_id,
    used_as_default_projector_for_motion_in_meeting_id,
    used_as_default_projector_for_amendment_in_meeting_id,
    used_as_default_projector_for_motion_block_in_meeting_id,
    used_as_default_projector_for_assignment_in_meeting_id,
    used_as_default_projector_for_mediafile_in_meeting_id,
    used_as_default_projector_for_message_in_meeting_id,
    used_as_default_projector_for_countdown_in_meeting_id,
    used_as_default_projector_for_assignment_poll_in_meeting_id,
    used_as_default_projector_for_motion_poll_in_meeting_id,
    used_as_default_projector_for_poll_in_meeting_id
)
VALUES (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2);
SELECT nextval('projector_t_id_seq');

INSERT INTO projector_t (id, meeting_id)
VALUES (3, 2);
SELECT nextval('projector_t_id_seq');

INSERT INTO group_t (id, name, meeting_id)
VALUES (3, 'gruppe3', 2);
SELECT nextval('group_t_id_seq');

COMMIT;

INSERT INTO organization_tag_t (id, name, color)
VALUES (2, 'bunt', '#ffffff');
SELECT nextval('organization_tag_t_id_seq');

INSERT INTO gm_organization_tag_tagged_ids_t (organization_tag_id, tagged_id)
VALUES (2, 'meeting/1');

BEGIN;
INSERT INTO topic_t (id, title, meeting_id)
VALUES (1, 'Thema1', 2);
SELECT nextval('topic_t_id_seq');

--list_of_speakers.content_object_id:topic.list_of_speakers_id gr:r
INSERT INTO list_of_speakers_t (
    id, content_object_id, sequential_number, meeting_id
)
VALUES (1, 'topic/1', 1, 2);

--agenda_item.content_object_id:topic.agenda_item_id gr:r
INSERT INTO agenda_item_t (content_object_id, meeting_id)
VALUES ('topic/1', 2);
COMMIT;

--rl:gr organization.mediafile_ids:mediafile.owner_id
INSERT INTO mediafile_t (id, owner_id)
VALUES (1, 'organization/1');

--rl:rl committee_ids:user_ids
INSERT INTO nm_committee_manager_ids_user_t (committee_id, user_id)
VALUES (1, 1);

COMMIT;
