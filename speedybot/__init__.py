"""SpeedyBot application package."""

VERSION = "4.1.0"


def install(core):
    """Initialize database migrations, policies, UI and handlers."""
    from . import context, storage, corepatch, handlers
    context.configure(core)
    storage.init_db()
    corepatch.apply()
    handlers.register()


def start_background():
    """Start package-owned background workers."""
    from . import updates

    updates.start()
