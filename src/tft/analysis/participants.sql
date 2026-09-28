-- Ranked participants from the verified set represented by the static catalog.
-- Untracked opponents remain available for observed lobby-copy calculations.
SELECT mp.match_id, mp.puuid, mp.placement, mp.level, mp.gold_left,
       mp.time_eliminated, mp.traits_json, mp.units_json,
       mp.augments_json, p.tier, m.game_version
FROM match_participants AS mp
LEFT JOIN players AS p ON mp.puuid = p.puuid
JOIN matches AS m ON mp.match_id = m.match_id
WHERE m.set_number = :set_number
  AND m.queue_id = :queue_id
  AND (:game_version IS NULL OR m.game_version = :game_version)
ORDER BY mp.match_id, mp.puuid;
