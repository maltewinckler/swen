-- SWEN Database Initialization
-- Creates all application databases on first PostgreSQL container start

-- Backend database
CREATE DATABASE swen;
GRANT ALL PRIVILEGES ON DATABASE swen TO postgres;

-- ML service database
CREATE DATABASE swen_ml;
GRANT ALL PRIVILEGES ON DATABASE swen_ml TO postgres;
