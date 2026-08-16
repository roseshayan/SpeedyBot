"""Register v4 user/admin handlers without touching the stable v3 handlers."""

def register():
    from . import user_handlers, admin_handlers
    user_handlers.register()
    admin_handlers.register()
