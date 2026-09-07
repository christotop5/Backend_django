from django.core.management.base import BaseCommand

from accounts.seed.runner import run_seed


class Command(BaseCommand):
    help = 'Seed VORA test data: 50 passengers, 10 drivers, 32 carrefours, 6 corridors (password: pass12345)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing seed users (vora.cm + fixture emails) before seeding',
        )

    def handle(self, *args, **options):
        stats = run_seed(flush=options['flush'])
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete — password: {stats['password']}\n"
            f"  zones: {stats['zones']}, carrefours: {stats['carrefours']}, "
            f"corridors: {stats['corridors']}\n"
            f"  passengers: {stats['passengers']}, drivers: {stats['drivers']}"
        ))
