"""SpeedyBot application package."""

VERSION = "4.0.0"


def install(core):
    """Initialize database migrations, policies, UI and handlers."""
    from . import context, storage, corepatch, handlers
    context.configure(core)
    storage.init_db()
    corepatch.apply()
    handlers.register()


def start_background():
    """Start package-owned background workers when added in future releases."""
    return None
