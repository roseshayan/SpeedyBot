"""Register SpeedyBot user/admin handlers."""


def register():
    from . import user_handlers, admin_handlers, admin_tools, trial, admin_ux, customization, linked_services

    user_handlers.register()
    admin_handlers.register()
    trial.register()
    admin_tools.register()
    # White-label/customer-menu callbacks use their own namespace and are
    # promoted so they cannot be swallowed by broader callback handlers.
    customization.register()
    # Promote linked-service handlers so view:linked callbacks override
    # the legacy read-only linked-service status handler.
    linked_services.register()
    # Register last so admin navigation also cancels pending steps when entering
    # customization. Unrelated callbacks continue to their namespace handlers.
    admin_ux.register()
