import time
from django.core.management.base import BaseCommand
from gestion.models import Evenement
from gestion.views import geocode_lieu


class Command(BaseCommand):
    help = "Géocode les événements existants qui n'ont pas encore de coordonnées GPS."

    def handle(self, *args, **options):
        evenements = Evenement.objects.filter(latitude__isnull=True).exclude(lieu='')
        count = 0
        for ev in evenements:
            lat, lon = geocode_lieu(ev.lieu)
            if lat and lon:
                ev.latitude = lat
                ev.longitude = lon
                ev.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f"✓ {ev.titre} → {lat}, {lon}"))
            else:
                self.stdout.write(self.style.WARNING(f"✗ {ev.titre} : géocodage échoué pour '{ev.lieu}'"))
            time.sleep(1)  # Nominatim limite à 1 requête/seconde
        self.stdout.write(self.style.SUCCESS(f"\n{count} événement(s) géocodé(s) au total."))