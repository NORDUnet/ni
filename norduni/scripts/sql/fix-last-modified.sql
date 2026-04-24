BEGIN;
UPDATE noclook_nodehandle
SET modified=upd.timestamp
FROM (SELECT MAX(timestamp) as timestamp, action_object_object_id FROM actstream_action GROUP BY action_object_object_id) as upd
WHERE upd.action_object_object_id=noclook_nodehandle.handle_id::varchar;
COMMIT;
