import itertools
from io import BytesIO

from django.contrib.staticfiles.finders import find as find_static
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from PIL import Image, ImageDraw, ImageFont

from gestion.models import (
    Agence, Structure, Langue, Action, Evenement, EvenementImage, Lieu,
    Realisation, RealisationLangue, Distribution
)

PALETTE = [
    (245, 130, 31), (10, 110, 58), (26, 26, 46), (180, 60, 40), (60, 90, 160),
]

# Noms de fichiers attendus dans static/img/demo/... — a placer toi-meme dans le repo.
# Le script boucle dessus (itertools.cycle), donc tu peux en mettre moins que necessaire.
IMAGES_REALISATIONS = ['r1.jpg', 'r2.jpg', 'r3.jpg', 'r4.jpg']
IMAGES_EVENEMENTS = ['e1.jpg', 'e2.jpg', 'e3.jpg']


def charger_image_statique(nom_relatif):
    """Cherche un fichier sous static/img/demo/... et retourne son contenu en ContentFile.
    Retourne None si le fichier n'existe pas encore (fallback vers une image generee)."""
    chemin = find_static(f"img/demo/{nom_relatif}")
    if not chemin:
        return None
    with open(chemin, 'rb') as f:
        return ContentFile(f.read())


def generer_image_secours(texte, taille=(900, 550), index=0):
    """Utilise seulement si aucune vraie image n'est trouvee dans static/img/demo/."""
    couleur = PALETTE[index % len(PALETTE)]
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
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((taille[0]-lw)/2, (taille[1]-lh)/2 - 10), texte, fill=(30, 30, 46), font=font)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Cree comptes + donnees de demo (actions, evenements geolocalises avec photos, realisations avec photos)."

    def handle(self, *args, **options):
        User = get_user_model()
        cycle_real = itertools.cycle(IMAGES_REALISATIONS)
        cycle_evt = itertools.cycle(IMAGES_EVENEMENTS)

        # -- Comptes --
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='NaftalDemo2026!')
            if hasattr(admin_user, 'role'):
                admin_user.role = 'admin'
                admin_user.save()
            self.stdout.write(self.style.SUCCESS("Compte admin cree : admin / NaftalDemo2026!"))
        else:
            admin_user = User.objects.get(username='admin')

        if not User.objects.filter(username='user').exists():
            demo_user = User.objects.create_user(username='user', email='user@example.com', password='12345')
            if hasattr(demo_user, 'role'):
                demo_user.role = 'user'
                demo_user.save()
            self.stdout.write(self.style.SUCCESS("Compte utilisateur cree : user / 12345"))

        # -- Reference --
        agence, _ = Agence.objects.get_or_create(nom="Agence Démonstration")
        structure, _ = Structure.objects.get_or_create(nom="Direction Réseau")
        langue_ar, _ = Langue.objects.get_or_create(nom="Arabe")
        langue_fr, _ = Langue.objects.get_or_create(nom="Français")
        lieu_boudouaou, _ = Lieu.objects.get_or_create(nom="Station Boudouaou", defaults={'type_lieu': 'station'})
        lieu_reghaia, _ = Lieu.objects.get_or_create(nom="Station Réghaïa", defaults={'type_lieu': 'station'})

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

        # -- Evenements avec vraies coordonnees (pas de geocodage reseau au build) --
        evenements_a_creer = [
            {'action': action_ramadan, 'titre': "Iftar communautaire — Alger", 'lieu': "Alger",
             'lat': 36.7538, 'lon': 3.0588, 'nb_photos': 3},
            {'action': action_ramadan, 'titre': "Distribution Ramadan — Boumerdès", 'lieu': "Boumerdès",
             'lat': 36.7669, 'lon': 3.4770, 'nb_photos': 2},
            {'action': action_securite, 'titre': "Journée sécurité routière — Béjaïa", 'lieu': "Béjaïa",
             'lat': 36.7509, 'lon': 5.0567, 'nb_photos': 3},
            {'action': action_portes, 'titre': "Portes ouvertes — Site Boudouaou", 'lieu': "Boudouaou",
             'lat': 36.7167, 'lon': 3.4667, 'nb_photos': 2},
            {'action': action_portes, 'titre': "Portes ouvertes — Site Réghaïa", 'lieu': "Réghaïa",
             'lat': 36.7590, 'lon': 3.3400, 'nb_photos': 3},
        ]

        for i, ev_data in enumerate(evenements_a_creer):
            evenement, created = Evenement.objects.get_or_create(
                action=ev_data['action'], titre=ev_data['titre'],
                defaults={
                    'lieu': ev_data['lieu'],
                    'date_debut': timezone.now().date(),
                    'latitude': ev_data['lat'],
                    'longitude': ev_data['lon'],
                }
            )
            if created:
                for j in range(ev_data['nb_photos']):
                    nom_fichier = next(cycle_evt)
                    contenu = charger_image_statique(nom_fichier) or generer_image_secours(ev_data['titre'], index=i + j)
                    img_ev = EvenementImage(evenement=evenement, ordre=j)
                    img_ev.image.save(f"evenement_{i}_{j}_{nom_fichier}", contenu, save=True)
                self.stdout.write(self.style.SUCCESS(f"Evenement '{ev_data['titre']}' cree ({ev_data['nb_photos']} photo(s), geolocalise)."))

        # -- Realisations --
        realisations_a_creer = [
            {'action': action_ramadan, 'type_support': 'depliant', 'titre_photo': "Dépliant Horaires Ramadan",
             'langues': {langue_ar: 1000, langue_fr: 800}, 'distribution': (lieu_boudouaou, langue_ar, 350)},
            {'action': action_ramadan, 'type_support': 'affiche', 'titre_photo': "Affiche Consignes Ramadan",
             'langues': {langue_ar: 500}, 'distribution': (lieu_boudouaou, langue_ar, 480)},
            {'action': action_securite, 'type_support': 'panneau', 'titre_photo': "Panneau Sécurité Routière",
             'langues': {langue_fr: 300}, 'distribution': None},
            {'action': action_portes, 'type_support': 'guide', 'titre_photo': "Guide Journées Portes Ouvertes",
             'langues': {langue_ar: 600, langue_fr: 600}, 'distribution': (lieu_reghaia, langue_fr, 200)},
        ]

        for i, r_data in enumerate(realisations_a_creer):
            realisation, created = Realisation.objects.get_or_create(
                action=r_data['action'], agence=agence, structure=structure, type_support=r_data['type_support'],
                defaults={'date': timezone.now().date(), 'cree_par': admin_user}
            )
            if created:
                nom_fichier = next(cycle_real)
                contenu = charger_image_statique(nom_fichier) or generer_image_secours(r_data['titre_photo'], index=i)
                realisation.image.save(f"realisation_{i}_{nom_fichier}", contenu, save=True)

                for langue, quantite in r_data['langues'].items():
                    RealisationLangue.objects.create(realisation=realisation, langue=langue, quantite=quantite)

                if r_data['distribution']:
                    lieu_d, langue_d, quantite_d = r_data['distribution']
                    Distribution.objects.create(
                        realisation=realisation, lieu=lieu_d, langue=langue_d,
                        quantite=quantite_d, date=timezone.now().date(), cree_par=admin_user,
                    )
                self.stdout.write(self.style.SUCCESS(f"Realisation '{r_data['titre_photo']}' creee."))

        self.stdout.write(self.style.SUCCESS("Seed termine : 3 actions, 5 evenements geolocalises, 4 realisations, photos reelles si disponibles."))