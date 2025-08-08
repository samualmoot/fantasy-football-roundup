from django.core.management.base import BaseCommand
from roundup.espn_utils import get_league

class Command(BaseCommand):
    help = 'Test ESPN API connection and print league/team info.'

    def handle(self, *args, **options):
        try:
            league = get_league()
            self.stdout.write(self.style.SUCCESS(f"League Name: {league.settings.name}"))
            self.stdout.write("Teams:")
            for team in league.teams:
                self.stdout.write(f"- {team.team_name}")
            # Print all attributes of the first team for inspection
            if league.teams:
                self.stdout.write("\nFirst team object attributes:")
                for attr, value in vars(league.teams[0]).items():
                    self.stdout.write(f"{attr}: {value}")
            # Print all attributes of the league object for documentation
            self.stdout.write("\nLeague object attributes:")
            for attr, value in vars(league).items():
                self.stdout.write(f"{attr}: {str(value)[:200]}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
