import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support
target_metadata = Base.metadata

# Set database URL dynamically from app settings


migration_url = make_url(get_settings().get_migration_database_url())
migration_role = get_settings().get_migration_database_role()

config.set_section_option(
    config.config_ini_section,
    "sqlalchemy.url",
    migration_url.render_as_string(hide_password=False).replace("%", "%%"),
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _quote_role_identifier(role_name: str) -> str:
    """Quote a simple PostgreSQL role identifier after validating its shape."""
    if (
        not role_name
        or not role_name.replace("_", "").isalnum()
        or role_name[0].isdigit()
    ):
        raise ValueError("Database role names must contain only letters, digits and underscores")
    return f'"{role_name}"'


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    runtime_role = make_url(get_settings().get_database_url()).username
    owner_role = migration_role or migration_url.username

    with context.begin_transaction():
        # Migration credentials may already be the owner. When role switching is
        # required, use an explicitly configured and validated owner role rather
        # than a hard-coded deployment-specific account name.
        if migration_role:
            connection.execute(text(f"SET LOCAL ROLE {_quote_role_identifier(migration_role)}"))

        # The runtime role is deliberately not the table owner. Grant it the
        # application DML privileges on existing tables and set default
        # privileges for objects created by the migration owner.
        if runtime_role and owner_role and runtime_role != owner_role:
            runtime_sql = _quote_role_identifier(runtime_role)
            owner_sql = _quote_role_identifier(owner_role)
            connection.execute(
                text(f"GRANT USAGE ON SCHEMA public TO {runtime_sql}")
            )
            connection.execute(
                text(
                    "GRANT SELECT, INSERT, UPDATE, DELETE "
                    f"ON ALL TABLES IN SCHEMA public TO {runtime_sql}"
                )
            )
            connection.execute(
                text(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
                    f"TO {runtime_sql}"
                )
            )
            connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE "
                    f"{owner_sql} IN SCHEMA public GRANT "
                    f"SELECT, INSERT, UPDATE, DELETE ON TABLES TO {runtime_sql}"
                )
            )
            connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE "
                    f"{owner_sql} IN SCHEMA public GRANT "
                    f"USAGE, SELECT ON SEQUENCES TO {runtime_sql}"
                )
            )

        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
