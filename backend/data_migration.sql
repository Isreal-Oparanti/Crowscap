-- SQL Migration to re-link mobile user data to the master user account for isrealopa@gmail.com

-- 1. Identify primary user ID (e.g. g_108304050162629490832 or first created user) for isrealopa@gmail.com
-- 2. Update memories, sources, captures, conversations, chat_messages, reminders to point to primary user ID

DO $$
DECLARE
    primary_id VARCHAR(36);
    secondary_id VARCHAR(36);
BEGIN
    SELECT id INTO primary_id FROM users WHERE email = 'isrealopa@gmail.com' ORDER BY created_at ASC LIMIT 1;
    
    FOR secondary_id IN SELECT id FROM users WHERE email = 'isrealopa@gmail.com' AND id != primary_id LOOP
        UPDATE memories SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE sources SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE captures SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE conversations SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE chat_messages SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE reminders SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE recall_reviews SET user_id = primary_id WHERE user_id = secondary_id;
        UPDATE user_preferences SET user_id = primary_id WHERE user_id = secondary_id;
        DELETE FROM users WHERE id = secondary_id;
    END LOOP;
END $$;
