"""Register SpeedyBot user/admin handlers."""


def register():
    from . import user_handlers, admin_handlers, admin_tools, trial, admin_ux

    user_handlers.register()
    admin_handlers.register()
    trial.register()
    admin_tools.register()
    # Register last: admin_ux promotes its guard/wizard callbacks ahead of the
    # legacy handlers while still allowing non-wizard actions to continue.
    admin_ux.register()
