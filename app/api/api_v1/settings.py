import os


TORTOISE_TEST_DB = "sqlite://app/tests/test-{}.sqlite3"
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                # set ENV variable
                "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
                "database": os.getenv("POSTGRES_DB", "fastapidb"),
            },
        }
    },
    "apps": {
        "models": {
            "models": ["app.api.api_v1.models.tortoise", "aerich.models"],
            # If no default_connection specified, defaults to 'default'
            "default_connection": "default",
        },
    },
}

CORS_MIDDLEWARE_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PATCH", "PUT", "DELETE"],
    "allow_headers": ["*"],
}
