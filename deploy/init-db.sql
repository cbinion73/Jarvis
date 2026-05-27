-- Create additional databases (ghostwritr is already created by POSTGRES_DB)
-- Chronicle can use the same postgres instance with its own DB if needed in future
CREATE DATABASE chronicle;
GRANT ALL PRIVILEGES ON DATABASE chronicle TO current_user;
