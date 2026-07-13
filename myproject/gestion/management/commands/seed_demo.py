from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from gestion.models import (
    Agence, Structure, Langue, Action, Evenement, Lieu,
    Realisation, RealisationLangue, Distribution
)


class Command(BaseCommand):
    help = "Crée un compte admin et des données de démonstration (idempotent — sans danger si relancé)."

    def handle(self, *args, **options):
        User = get_user_model()

        # ── Compte admin de démonstration ──
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='NaftalDemo2026!'
            )
            # Si ton modèle Utilisateur a un champ 'role', on le force à 'admin'
            if hasattr(admin_user, 'role'):
                admin_user.role = 'admin'
                admin_user.save()
            self.stdout.write(self.style.SUCCESS(
                "Compte admin créé -> identifiant: admin / mot de passe: NaftalDemo2026!"
            ))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write("Compte admin déjà présent.")

        # ── Compte utilisateur simple de démonstration ──
        if not User.objects.filter(username='demo').exists():
            demo_user = User.objects.create_user(
                username='demo',
                email='demo@example.com',
                password='NaftalDemo2026!'
            )
            if hasattr(demo_user, 'role'):
                demo_user.role = 'user'
                demo_user.save()
            self.stdout.write(self.style.SUCCESS(
                "Compte utilisateur créé -> identifiant: demo / mot de passe: NaftalDemo2026!"
            ))

        # ── Données de référence ──
        agence, _ = Agence.objects.get_or_create(nom="Agence Démonstration")
        structure, _ = Structure.objects.get_or_create(nom="Direction Réseau")
        langue_ar, _ = Langue.objects.get_or_create(nom="Arabe")
        langue_fr, _ = Langue.objects.get_or_create(nom="Français")
        lieu, _ = Lieu.objects.get_or_create(
            nom="Station Boudouaou", defaults={'type_lieu': 'station'}
        )

        action, _ = Action.objects.get_or_create(
            nom="Campagne de démonstration 2026",
            defaults={'description': "Action créée automatiquement pour la démonstration du site."}
        )

        Evenement.objects.get_or_create(
            action=action,
            titre="Journée portes ouvertes (démo)",
            defaults={
                'lieu': "Station Boudouaou",
                'date_debut': timezone.now().date(),
            }
        )

        # ── Une réalisation de démonstration, avec quantités par langue ──
        realisation, created = Realisation.objects.get_or_create(
            action=action,
            agence=agence,
            structure=structure,
            type_support='depliant',
            defaults={
                'date': timezone.now().date(),
                'cree_par': admin_user,
            }
        )

        if created:
            RealisationLangue.objects.create(realisation=realisation, langue=langue_ar, quantite=1000)
            RealisationLangue.objects.create(realisation=realisation, langue=langue_fr, quantite=800)

            Distribution.objects.create(
                realisation=realisation,
                lieu=lieu,
                langue=langue_ar,
                quantite=200,
                date=timezone.now().date(),
                cree_par=admin_user,
            )
            self.stdout.write(self.style.SUCCESS("Réalisation de démonstration créée."))
        else:
            self.stdout.write("Réalisation de démonstration déjà présente.")

        self.stdout.write(self.style.SUCCESS("Seed terminé avec succès."))