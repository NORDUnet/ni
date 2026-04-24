BEGIN;
SELECT setval(pg_get_serial_sequence('"noclook_nodetype"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_nodetype";
SELECT setval(pg_get_serial_sequence('"noclook_nodehandle"','handle_id'), coalesce(max("handle_id"), 1), max("handle_id") IS NOT null) FROM "noclook_nodehandle";
SELECT setval(pg_get_serial_sequence('"noclook_uniqueidgenerator"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_uniqueidgenerator";
SELECT setval(pg_get_serial_sequence('"noclook_nordunetuniqueid"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "noclook_nordunetuniqueid";
COMMIT;