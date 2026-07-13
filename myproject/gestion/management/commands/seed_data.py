from django.core.management.base import BaseCommand
from gestion.models import (
    Utilisateur, Agence, Action, Evenement,
    Structure, Langue, Lieu, Realisation, RealisationLangue, Distribution
)
from datetime import date


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')

        # --- Langues ---
        arabe, _    = Langue.objects.get_or_create(nom='Arabe')
        francais, _ = Langue.objects.get_or_create(nom='Français')
        anglais, _  = Langue.objects.get_or_create(nom='Anglais')
        self.stdout.write('  ✓ Langues')

        # --- Agences ---
        quartz, _      = Agence.objects.get_or_create(nom='Quartz Communication')
        anep, _        = Agence.objects.get_or_create(nom='ANEP Communication Signalétique')
        express, _     = Agence.objects.get_or_create(nom='Express Solution')
        anep_rouiba, _ = Agence.objects.get_or_create(nom='ANEP Rouiba')
        self.stdout.write('  ✓ Agences')

        # --- Structures ---
        structure_comm, _   = Structure.objects.get_or_create(nom='Service Communication')
        structure_naftal, _ = Structure.objects.get_or_create(nom='Service NAFTAL')
        self.stdout.write('  ✓ Structures')

        # --- Actions ---
        action_foire, _ = Action.objects.get_or_create(
            nom="46e Foire internationale",
            defaults={'description': 'Foire internationale de la production nationale'}
        )
        action_hiver, _ = Action.objects.get_or_create(
            nom="Campagne de sensibilisation hivernale 2013/2014",
            defaults={'description': 'Campagne sécurité bouteille gaz'}
        )
        self.stdout.write('  ✓ Actions')

        # --- Événements ---
        Evenement.objects.get_or_create(
            action=action_foire,
            titre="46e Foire Internationale d'Alger",
            defaults={
                'lieu': 'Palais des Expositions, Alger',
                'date_debut': date(2013, 5, 29),
                'date_fin': date(2013, 6, 3),
            }
        )
        Evenement.objects.get_or_create(
            action=action_foire,
            titre="Visite du ministre tanzanien",
            defaults={
                'lieu': 'CE SIDI ARCINE',
                'date_debut': date(2013, 12, 3),
                'date_fin': date(2013, 12, 3),
            }
        )
        Evenement.objects.get_or_create(
            action=action_hiver,
            titre="Campagne hivernale — période 2013/2014",
            defaults={
                'lieu': 'Réseau stations Naftal',
                'date_debut': date(2013, 10, 1),
                'date_fin': date(2014, 3, 31),
            }
        )
        Evenement.objects.get_or_create(
            action=action_hiver,
            titre="Caravane de sensibilisation 2e édition",
            defaults={
                'lieu': 'Tlemcen, Chlef',
                'date_debut': date(2013, 11, 1),
                'date_fin': date(2014, 2, 28),
            }
        )
        self.stdout.write('  ✓ Événements')

        # --- Lieux ---
        lieux_data = [
            ('Station Mazafran',      'station'),
            ('Station Cheraga',       'station'),
            ('Station Sissan',        'station'),
            ('Station Didouche Mourad','station'),
            ("Station l'Ain",         'station'),
            ('Station Carroubier',    'station'),
            ('Station El Bahdja',     'station'),
            ('Station Boumerdes',     'station'),
            ('Tlemcen',               'wilaya'),
            ('Chlef',                 'wilaya'),
        ]
        lieux = {}
        for nom, type_lieu in lieux_data:
            lieu, _ = Lieu.objects.get_or_create(nom=nom, defaults={'type_lieu': type_lieu})
            lieux[nom] = lieu
        self.stdout.write('  ✓ Lieux')

        # --- Réalisations ---
        r1, _ = Realisation.objects.get_or_create(
            type_support='depliant',
            agence=quartz,
            action=action_foire,
            structure=structure_comm,
            defaults={'date': date(2013, 5, 29)}
        )
        RealisationLangue.objects.get_or_create(realisation=r1, langue=arabe,    defaults={'quantite': 700})
        RealisationLangue.objects.get_or_create(realisation=r1, langue=anglais,  defaults={'quantite': 300})
        RealisationLangue.objects.get_or_create(realisation=r1, langue=francais, defaults={'quantite': 1000})

        r2, _ = Realisation.objects.get_or_create(
            type_support='affiche',
            agence=anep,
            action=action_foire,
            structure=structure_comm,
            defaults={'date': date(2013, 5, 29)}
        )
        RealisationLangue.objects.get_or_create(realisation=r2, langue=arabe,    defaults={'quantite': 1})

        r3, _ = Realisation.objects.get_or_create(
            type_support='panneau',
            agence=anep,
            action=action_hiver,
            structure=structure_naftal,
            defaults={'date': date(2013, 10, 1)}
        )
        RealisationLangue.objects.get_or_create(realisation=r3, langue=arabe,    defaults={'quantite': 11})

        r4, _ = Realisation.objects.get_or_create(
            type_support='prospectus',
            agence=express,
            action=action_hiver,
            structure=structure_naftal,
            defaults={'date': date(2013, 10, 1)}
        )
        RealisationLangue.objects.get_or_create(realisation=r4, langue=arabe,    defaults={'quantite': 1750})
        RealisationLangue.objects.get_or_create(realisation=r4, langue=francais, defaults={'quantite': 1750})

        r5, _ = Realisation.objects.get_or_create(
            type_support='affiche',
            agence=anep_rouiba,
            action=action_hiver,
            structure=structure_naftal,
            defaults={'date': date(2013, 10, 1)}
        )
        RealisationLangue.objects.get_or_create(realisation=r5, langue=arabe,    defaults={'quantite': 40000})
        RealisationLangue.objects.get_or_create(realisation=r5, langue=francais, defaults={'quantite': 25000})

        self.stdout.write('  ✓ Réalisations + langues')

        # --- Distributions ---
        Distribution.objects.get_or_create(
            realisation=r1, lieu=lieux['Station Mazafran'], langue=arabe,
            defaults={'quantite': 450, 'date': date(2013, 12, 5)}
        )
        Distribution.objects.get_or_create(
            realisation=r4, lieu=lieux['Station Cheraga'], langue=arabe,
            defaults={'quantite': 200, 'date': date(2014, 1, 10)}
        )
        Distribution.objects.get_or_create(
            realisation=r4, lieu=lieux['Station Sissan'], langue=arabe,
            defaults={'quantite': 300, 'date': date(2014, 1, 15)}
        )
        Distribution.objects.get_or_create(
            realisation=r5, lieu=lieux['Tlemcen'], langue=arabe,
            defaults={'quantite': 2500, 'date': date(2014, 2, 1)}
        )
        Distribution.objects.get_or_create(
            realisation=r5, lieu=lieux['Chlef'], langue=francais,
            defaults={'quantite': 2250, 'date': date(2014, 2, 5)}
        )
        self.stdout.write('  ✓ Distributions')

        # --- Utilisateurs ---
        if not Utilisateur.objects.filter(username='agent1').exists():
            Utilisateur.objects.create_user(
                username='agent1', password='test1234', role='user'
            )
            self.stdout.write('  ✓ User: agent1 / test1234')

        self.stdout.write(self.style.SUCCESS('\n✅ Seeding terminé avec succès !'))