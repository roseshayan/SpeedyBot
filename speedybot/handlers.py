"""Register SpeedyBot user/admin handlers."""


def register():
    from . import user_handlers, admin_handlers, admin_tools, trial

    user_handlers.register()
    admin_handlers.register()
    trial.register()
    admin_tools.register()
