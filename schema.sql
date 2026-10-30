BEGIN;

-- 活動資料
CREATE TABLE activities (
    activity_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(200) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    capacity INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (capacity > 0),
    CHECK (end_time > start_time),
    CHECK (deadline <= start_time),
    CHECK (length(trim(title)) > 0),
    CHECK (length(trim(location)) > 0)
);

-- 報名者資料
CREATE TABLE participants (
    participant_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(email)) > 0),
    CHECK (email = lower(trim(email)))
);

-- 報名紀錄
CREATE TABLE registrations (
    registration_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    participant_id INTEGER NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (activity_id)
        REFERENCES activities(activity_id),

    FOREIGN KEY (participant_id)
        REFERENCES participants(participant_id),

    UNIQUE (activity_id, participant_id)
);

COMMIT;