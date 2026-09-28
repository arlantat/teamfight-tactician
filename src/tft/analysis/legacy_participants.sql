-- Preserve historical analysis scope when no catalog set metadata is available.
-- This query supports match tables predating set and queue provenance columns.
SELECT mp.match_id, mp.puuid, mp.placement, mp.level, mp.gold_left,
       mp.time_eliminated, mp.traits_json, mp.units_json,
       mp.augments_json, p.tier, m.game_version
FROM match_participants AS mp
LEFT JOIN players AS p ON mp.puuid = p.puuid
JOIN matches AS m ON mp.match_id = m.match_id
WHERE (:game_version IS NULL OR m.game_version = :game_version)
ORDER BY mp.match_id, mp.puuid;
