VERSION="4.0.0"

def install(core):
    from . import context, storage, corepatch, handlers
    context.configure(core)
    storage.init_db()
    corepatch.apply()
    handlers.register()

def start_background():
    return
