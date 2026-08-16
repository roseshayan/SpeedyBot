"""SpeedyBot production entrypoint.

SpeedyBot v4 is a single integrated application. The business core and the
Control Center live in the ``speedybot`` package; this file is the canonical
runtime entrypoint used by systemd, manual runs, installation and updates.
"""
from speedybot import core
import speedybot


def run():
    speedybot.install(core)
    print(f"SpeedyBot {speedybot.VERSION} is running...")
    core.bot.remove_webhook()
    core.recover_processing_transactions()
    core.reconcile_missing_referral_commissions()
    core.start_startup_panel_reconcile()
    core.start_service_monitor()
    speedybot.start_background()
    core.bot.infinity_polling()


if __name__ == "__main__":
    run()
