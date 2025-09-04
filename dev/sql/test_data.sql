-- This script should only be used for an database filled with base_data.sql.

--relation --relation-list gender_ids
INSERT INTO gender_t (name) VALUES ('female');
INSERT INTO user_t (username, gender_id) VALUES ('tom', 1);

BEGIN;

INSERT INTO motion_state_t (id, name, weight, workflow_id, meeting_id)
VALUES (5, 'motionState5', 1, 2, 2);

INSERT INTO motion_workflow_t (
    id, name, sequential_number, first_state_id, meeting_id
)
VALUES (2, 'workflow2', 2, 4, 2);

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
INSERT INTO organization_tag_t (id, name, color)

--generic-relation-list tagged_ids
VALUES (1, 'tagA', '#cc3b03');

--relation-list organization_tag_ids --relation 1:1 default_meeting_id
INSERT INTO committee (id, name, default_meeting_id)
VALUES (2, 'plenum', 2);

INSERT INTO projector_t (id, sequential_number, meeting_id)
VALUES (2, 2, 2);

INSERT INTO group_t (id, name, meeting_id)
VALUES (3, 'gruppe3', 2);

COMMIT;

INSERT INTO organization_tag_t (id, name, color)
VALUES (2, 'bunt', '#ffffff');

INSERT INTO gm_organization_tag_tagged_ids_t (organization_tag_id, tagged_id)
VALUES (2, 'meeting/1');

INSERT INTO topic_t (id, title, sequential_number, meeting_id)
VALUES (1, 'Thema1', 1, 2);

--agenda_item.content_object_id:topic.agenda_item_id gr:r
INSERT INTO agenda_item_t (content_object_id, meeting_id)
VALUES ('topic/1', 2);

--rl:gr topic.poll_ids:poll.content_object_id
INSERT INTO poll_t (
    id,
    title,
    type,
    backend,
    pollmethod,
    onehundred_percent_base,
    sequential_number,
    content_object_id,
    meeting_id
)
VALUES (1, 'Titel1', 'analog', 'fast', 'YNA', 'disabled', 1, 'topic/1', 2);

--rl:rl committee_ids:user_ids
INSERT INTO nm_committee_manager_ids_user_t (committee_id, user_id)
VALUES (1, 1);

COMMIT;
