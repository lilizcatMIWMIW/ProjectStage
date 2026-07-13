from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from PIL import Image, ImageDraw, ImageFont

from gestion.models import (
    Agence, Structure, Langue, Action, Evenement, EvenementImage, Lieu,
    Realisation, RealisationLangue, Distribution
)

# Palette de couleurs utilisée pour générer les visuels de démonstration
PALETTE = [
    (245, 130, 31),   # orange Naftal
    (10, 110, 58),    # vert
    (26, 26, 46),     # bleu nuit
    (180, 60, 40),    # brique
    (60, 90, 160),    # bleu
]


def generer_image(texte, taille=(900, 550), couleur=None, index=0):
    """Genere une image PNG de demonstration a la volee (pas besoin de vraies photos)."""
    couleur = couleur or PALETTE[index % len(PALETTE)]
    img = Image.new('RGB', taille, color=couleur)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.load_default(size=42)
    except TypeError:
        font = ImageFont.load_default()

    bande_haut = taille[1] // 2 - 60
    bande_bas = taille[1] // 2 + 60
    draw.rectangle([(0, bande_haut), (taille[0], bande_bas)], fill=(255, 255, 255))

    bbox = draw.textbbox((0, 0), texte, font=font)
    largeur_texte = bbox[2] - bbox[0]
    hauteur_texte = bbox[3] - bbox[1]
    position = ((taille[0] - largeur_texte) / 2, (taille[1] - hauteur_texte) / 2 - 10)
    draw.text(position, texte, fill=(30, 30, 46), font=font)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Cree des comptes de demonstration et remplit la base avec des actions, evenements (avec photos) et realisations (avec photos)."

    def handle(self, *args, **options):
        User = get_user_model()

        # -- Compte admin --
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin', email='admin@example.com', password='NaftalDemo2026!'
            )
            if hasattr(admin_user, 'role'):
                admin_user.role = 'admin'
                admin_user.save()
            self.stdout.write(self.style.SUCCESS("Compte admin cree : admin / NaftalDemo2026!"))
        else:
            admin_user = User.objects.get(username='admin')

        # -- Compte utilisateur simple : username=user / password=12345 --
        if not User.objects.filter(username='user').exists():
            demo_user = User.objects.create_user(
                username='user', email='user@example.com', password='12345'
            )
            if hasattr(demo_user, 'role'):
                demo_user.role = 'user'
                demo_user.save()
            self.stdout.write(self.style.SUCCESS("Compte utilisateur cree : user / 12345"))

        # -- Donnees de reference --
        agence, _ = Agence.objects.get_or_create(nom="Agence Démonstration")
        structure, _ = Structure.objects.get_or_create(nom="Direction Réseau")
        langue_ar, _ = Langue.objects.get_or_create(nom="Arabe")
        langue_fr, _ = Langue.objects.get_or_create(nom="Français")
        lieu_boudouaou, _ = Lieu.objects.get_or_create(nom="Station Boudouaou", defaults={'type_lieu': 'station'})
        lieu_reghaia, _ = Lieu.objects.get_or_create(nom="Station Réghaïa", defaults={'type_lieu': 'station'})
        lieu_bejaia, _ = Lieu.objects.get_or_create(nom="Wilaya de Béjaïa", defaults={'type_lieu': 'wilaya'})

        # -- 3 actions --
        action_ramadan, _ = Action.objects.get_or_create(
            nom="Campagne Ramadan 2026",
            defaults={'description': "Distribution de dépliants informatifs durant le mois de Ramadan."}
        )
        action_securite, _ = Action.objects.get_or_create(
            nom="Sécurité Routière — Sensibilisation",
            defaults={'description': "Campagne de sensibilisation à la sécurité routière autour des stations GPL."}
        )
        action_portes, _ = Action.objects.get_or_create(
            nom="Journées Portes Ouvertes GPL",
            defaults={'description': "Journées de présentation du GPL au grand public sur plusieurs sites."}
        )

        # -- 5 evenements, repartis sur les 3 actions, avec 2 a 3 photos chacun --
        evenements_a_creer = [
            {
                'action': action_ramadan, 'titre': "Iftar communautaire — Alger",
                'lieu': "Alger Centre", 'nb_photos': 3,
            },
            {
                'action': action_ramadan, 'titre': "Distribution Ramadan — Boumerdès",
                'lieu': "Boumerdès", 'nb_photos': 2,
            },
            {
                'action': action_securite, 'titre': "Journée sécurité routière — Béjaïa",
                'lieu': "Béjaïa", 'nb_photos': 3,
            },
            {
                'action': action_portes, 'titre': "Portes ouvertes — Site Boudouaou",
                'lieu': "Boudouaou", 'nb_photos': 2,
            },
            {
                'action': action_portes, 'titre': "Portes ouvertes — Site Réghaïa",
                'lieu': "Réghaïa", 'nb_photos': 3,
            },
        ]

        for i, ev_data in enumerate(evenements_a_creer):
            evenement, created = Evenement.objects.get_or_create(
                action=ev_data['action'],
                titre=ev_data['titre'],
                defaults={
                    'lieu': ev_data['lieu'],
                    'date_debut': timezone.now().date(),
                }
            )
            if created:
                for j in range(ev_data['nb_photos']):
                    img_ev = EvenementImage(evenement=evenement, ordre=j)
                    img_ev.image.save(
                        f"evenement_{i}_{j}.png",
                        generer_image(ev_data['titre'], index=i + j),
                        save=True,
                    )
                self.stdout.write(self.style.SUCCESS(
                    f"Evenement '{ev_data['titre']}' cree avec {ev_data['nb_photos']} photo(s)."
                ))

        # -- Realisations avec photo, reparties sur les 3 actions --
        realisations_a_creer = [
            {
                'action': action_ramadan, 'type_support': 'depliant',
                'titre_photo': "Dépliant Horaires Ramadan",
                'langues': {langue_ar: 1000, langue_fr: 800},
                'distribution': (lieu_boudouaou, langue_ar, 350),
            },
            {
                'action': action_ramadan, 'type_support': 'affiche',
                'titre_photo': "Affiche Consignes Ramadan",
                'langues': {langue_ar: 500},
                'distribution': (lieu_boudouaou, langue_ar, 480),
            },
            {
                'action': action_securite, 'type_support': 'panneau',
                'titre_photo': "Panneau Sécurité Routière",
                'langues': {langue_fr: 300},
                'distribution': None,
            },
            {
                'action': action_portes, 'type_support': 'guide',
                'titre_photo': "Guide Journées Portes Ouvertes",
                'langues': {langue_ar: 600, langue_fr: 600},
                'distribution': (lieu_reghaia, langue_fr, 200),
            },
        ]

        for i, r_data in enumerate(realisations_a_creer):
            realisation, created = Realisation.objects.get_or_create(
                action=r_data['action'],
                agence=agence,
                structure=structure,
                type_support=r_data['type_support'],
                defaults={
                    'date': timezone.now().date(),
                    'cree_par': admin_user,
                }
            )
            if created:
                realisation.image.save(
                    f"realisation_{i}.png",
                    generer_image(r_data['titre_photo'], index=i),
                    save=True,
                )
                for langue, quantite in r_data['langues'].items():
                    RealisationLangue.objects.create(realisation=realisation, langue=langue, quantite=quantite)

                if r_data['distribution']:
                    lieu_d, langue_d, quantite_d = r_data['distribution']
                    Distribution.objects.create(
                        realisation=realisation, lieu=lieu_d, langue=langue_d,
                        quantite=quantite_d, date=timezone.now().date(), cree_par=admin_user,
                    )
                self.stdout.write(self.style.SUCCESS(
                    f"Realisation '{r_data['titre_photo']}' creee avec photo."
                ))

        self.stdout.write(self.style.SUCCESS("Seed termine : 3 actions, 5 evenements, 4 realisations, toutes avec photos."))