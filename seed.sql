-- 測試資料：可報名、額滿、已截止 各一場（時間以匯入當下為基準）
BEGIN;

INSERT INTO activities (title, description, location, start_time, end_time, deadline, capacity) VALUES
('FastAPI 入門工作坊', '從零開始建立第一個 FastAPI 專案。', '資訊大樓 301',
	date_trunc('hour', now()) + interval '14 days', date_trunc('hour', now()) + interval '14 days 3 hours',
	date_trunc('hour', now()) + interval '10 days', 30),
('PostgreSQL 交易實戰', '名額有限，示範額滿狀態。', '資訊大樓 205',
	date_trunc('hour', now()) + interval '7 days', date_trunc('hour', now()) + interval '7 days 2 hours',
	date_trunc('hour', now()) + interval '5 days', 2),
('期中專題發表會', '示範已截止狀態。', '國際會議廳',
	date_trunc('hour', now()) + interval '2 days', date_trunc('hour', now()) + interval '2 days 4 hours',
	date_trunc('hour', now()) - interval '1 day', 50);

INSERT INTO participants (name, email) VALUES
('王小明', 'ming@example.com'),
('李小華', 'hua@example.com');

-- 讓「PostgreSQL 交易實戰」額滿
INSERT INTO registrations (activity_id, participant_id)
SELECT a.activity_id, p.participant_id
FROM activities a, participants p
WHERE a.title = 'PostgreSQL 交易實戰';

COMMIT;
