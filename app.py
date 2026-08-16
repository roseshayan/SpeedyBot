"""Production entrypoint for SpeedyBot v4.

The stable v3 core remains in main.py. v4 product/UX extensions are installed
before polling starts, so upgrades are additive and rollback-friendly.
"""
import main
import speedybot_plus

speedybot_plus.install(main)

if __name__ == '__main__':
    print('SpeedyBot v4 is running...')
    main.bot.remove_webhook()
    main.recover_processing_transactions()
    main.reconcile_missing_referral_commissions()
    main.start_startup_panel_reconcile()
    main.start_service_monitor()
    speedybot_plus.start_background()
    main.bot.infinity_polling()
