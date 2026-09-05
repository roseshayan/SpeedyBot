"""Register SpeedyBot user/admin handlers."""


def register():
    from . import user_handlers, admin_handlers, admin_tools, trial, admin_ux, customization, linked_services

    user_handlers.register()
    admin_handlers.register()
    trial.register()
    admin_tools.register()
    # Register last: admin_ux promotes its guard/wizard callbacks ahead of the
    # legacy handlers while still allowing non-wizard actions to continue.
    admin_ux.register()
    # White-label/customer-menu callbacks use their own namespace and are
    # promoted so they cannot be swallowed by broader callback handlers.
    customization.register()
    # Register linked-service handlers last so view:linked callbacks override
    # the legacy read-only linked-service status handler.
    linked_services.register()
