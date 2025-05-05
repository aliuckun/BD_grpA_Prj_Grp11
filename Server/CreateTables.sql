CREATE DATABASE ocpp_db
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'tr-TR'
    LC_CTYPE = 'tr-TR'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

CREATE TABLE ocpp_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    direction VARCHAR(10) CHECK (direction IN ('incoming', 'outgoing')),
    charge_point_id VARCHAR(50),
    message_type VARCHAR(50),
    payload JSONB
);

CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    charge_point_id VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT
);
