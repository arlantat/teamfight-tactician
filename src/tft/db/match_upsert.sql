INSERT INTO matches (
    match_id, game_version, set_number, game_datetime, queue_id, participant_count
) VALUES (
    :match_id, :game_version, :set_number, :game_datetime, :queue_id, :participant_count
)
ON CONFLICT (match_id) DO UPDATE SET
    game_version = excluded.game_version,
    set_number = excluded.set_number,
    game_datetime = excluded.game_datetime,
    queue_id = excluded.queue_id,
    participant_count = excluded.participant_count;
