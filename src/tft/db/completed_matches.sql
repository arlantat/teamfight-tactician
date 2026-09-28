SELECT matches.match_id
FROM matches
JOIN match_participants USING (match_id)
WHERE matches.set_number = ?
  AND matches.queue_id = ?
  AND matches.game_datetime IS NOT NULL
  AND matches.participant_count > 0
GROUP BY matches.match_id
HAVING COUNT(match_participants.puuid) = matches.participant_count;
