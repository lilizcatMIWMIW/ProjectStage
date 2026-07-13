from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Realisation, Action, Langue, Agence, Structure, Evenement, EvenementImage, Lieu, Distribution
from .forms import RealisationForm
from django.shortcuts import get_object_or_404
import json
import requests
from django.core.exceptions import ValidationError
from functools import wraps
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum
from .models import Utilisateur, RealisationLangue


def geocode_lieu(lieu):
    """Convertit un nom de lieu (ex: 'Alger') en coordonnées GPS via Nominatim (OpenStreetMap, gratuit)."""
    if not lieu:
        return None, None
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{lieu}, Algérie", "format": "json", "limit": 1},
            headers={"User-Agent": "NaftalGPL-App/1.0"},
            timeout=5
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def connexion_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_dashboard')
            return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, 'gestion/login.html')
def deconnexion_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):
    query = request.GET.get('q', '')
    date_filter = request.GET.get('date', '')

    realisations = Realisation.objects.select_related(
        'agence', 'action', 'structure'
    ).prefetch_related('langues__langue').order_by('-date')

    if query:
        realisations = realisations.filter(
            Q(action__nom__icontains=query) |
            Q(type_support__icontains=query) |
            Q(structure__nom__icontains=query)
        )

    if date_filter:
        realisations = realisations.filter(date__year=date_filter)

    realisations_recentes = realisations[:6]

    actions = Action.objects.prefetch_related(
        'evenements__images'
    ).all().order_by('nom')

    context = {
        'realisations_recentes': realisations_recentes,
        'actions': actions,
        'query': query,
        'date_filter': date_filter,
    }
    return render(request, 'gestion/home.html', context)


@login_required(login_url='login')
def realisation_list(request):
    realisations = Realisation.objects.select_related(
        'agence', 'action', 'structure'
    ).prefetch_related('langues__langue').order_by('-date')

    action_id = request.GET.get('action')
    langue_id = request.GET.get('langue')
    type_support = request.GET.get('type_support')
    annee = request.GET.get('annee')

    selected_action = int(action_id) if action_id else None
    selected_langue = int(langue_id) if langue_id else None

    if action_id:
        realisations = realisations.filter(action__id=action_id)
    if langue_id:
        realisations = realisations.filter(langues__langue__id=langue_id)
    if type_support:
        realisations = realisations.filter(type_support=type_support)
    if annee:
        realisations = realisations.filter(date__year=annee)

    context = {
        'realisations': realisations,
        'actions': Action.objects.all().order_by('nom'),
        'langues': Langue.objects.all(),
        'type_choices': Realisation.TYPE_SUPPORT_CHOICES,
        'annees': Realisation.objects.dates('date', 'year', order='DESC'),
        'selected_action': selected_action,
        'selected_langue': selected_langue,
        'selected_type': type_support,
        'selected_annee': annee,
    }
    return render(request, 'gestion/realisation_list.html', context)


@login_required(login_url='login')
def realisation_create(request):
    if request.method == 'POST':
        from .models import RealisationLangue, Evenement, EvenementImage
        import json

        # ── monn acrion ──
        action_mode = request.POST.get('action_mode', 'existing')
        if action_mode == 'new':
            action_nom = request.POST.get('action_nom', '').strip()
            if not action_nom:
                messages.error(request, "Le nom de l'action est requis.")
                return redirect('realisation_create')
            from .models import Action as ActionModel
            action_obj, _ = ActionModel.objects.get_or_create(
                nom=action_nom,
                defaults={'description': request.POST.get('action_description', '')}
            )
        else:
            action_id = request.POST.get('action_existante')
            if not action_id:
                messages.error(request, "Veuillez sélectionner ou créer une action.")
                return redirect('realisation_create')
            try:
                action_obj = Action.objects.get(id=action_id)
            except Action.DoesNotExist:
                messages.error(request, "Action introuvable.")
                return redirect('realisation_create')

        # ──gerer les evenements ──
        event_count = int(request.POST.get('event_count', 0))
        for i in range(event_count):
            titre = request.POST.get(f'event_titre_{i}', '').strip()
            if titre:
                lieu_val = request.POST.get(f'event_lieu_{i}', '')
                lat, lon = geocode_lieu(lieu_val)
                Evenement.objects.create(
                    action=action_obj,
                    titre=titre,
                    lieu=lieu_val,
                    date_debut=request.POST.get(f'event_debut_{i}') or None,
                    date_fin=request.POST.get(f'event_fin_{i}') or None,
                    latitude=lat,
                    longitude=lon,
                )

        # ── TYPE SUPPORTt ──
        type_support = request.POST.get('type_support', '')
        if type_support == 'autre':
            type_support_autre = request.POST.get('type_support_autre', '').strip()
            if not type_support_autre:
                messages.error(request, "Précisez le type de support.")
                return redirect('realisation_create')
            type_support = 'autre'

        # ── REALISATIONS ──
        agence_id = request.POST.get('agence')
        structure_id = request.POST.get('structure')
        date_val = request.POST.get('date')

        if not all([type_support, agence_id, structure_id, date_val]):
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('realisation_create')

        try:
            realisation = Realisation.objects.create(
                type_support=type_support,
                agence=Agence.objects.get(id=agence_id),
                action=action_obj,
                structure=Structure.objects.get(id=structure_id),
                date=date_val,
                cree_par=request.user,
                image=request.FILES.get('image') or None,
            )
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {e}")
            return redirect('realisation_create')

        # ── LANGUES ──
        langue_count = int(request.POST.get('langue_count', 0))
        langues_ajoutees = 0
        for i in range(langue_count):
            langue_id = request.POST.get(f'langue_id_{i}', '').strip()
            quantite_str = request.POST.get(f'langue_qte_{i}', '').strip()
            if langue_id and quantite_str:
                try:
                    from .models import Langue as LangueModel, RealisationLangue
                    langue_obj = LangueModel.objects.get(id=int(langue_id))
                    RealisationLangue.objects.create(
                        realisation=realisation,
                        langue=langue_obj,
                        quantite=int(quantite_str)
                    )
                    langues_ajoutees += 1
                except Exception:
                    pass

        if langues_ajoutees == 0:
            messages.warning(request, "Réalisation créée mais aucune langue n'a été ajoutée.")

        # ── GERER LES IMGS DES EVENENT SICI ──
        for i in range(event_count):
            titre = request.POST.get(f'event_titre_{i}', '').strip()
            if titre:
                ev = Evenement.objects.filter(
                    action=action_obj, titre=titre
                ).last()
                if ev:
                    for j in range(3):
                        img_file = request.FILES.get(f'event_img_{i}_{j}')
                        if img_file:
                            from .models import EvenementImage
                            EvenementImage.objects.create(
                                evenement=ev,
                                image=img_file,
                                ordre=j
                            )

        messages.success(request, "Réalisation ajoutée avec succès !")
        return redirect('home')

    # GET
    context = {
        'actions': Action.objects.all().order_by('nom'),
        'agences': Agence.objects.all().order_by('nom'),
        'structures': Structure.objects.all().order_by('nom'),
        'langues': Langue.objects.all(),
    }
    return render(request, 'gestion/realisation_create.html', context)


@login_required(login_url='login')
def realisation_detail(request, pk):
    realisation = get_object_or_404(
        Realisation.objects.select_related('agence', 'action', 'structure').prefetch_related(
            'langues__langue', 'distributions__lieu', 'distributions__langue'
        ),
        pk=pk
    )

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # ── FORM de mdofif les info──
        if form_type == 'edit':
            type_support = request.POST.get('type_support', '').strip()
            agence_id = request.POST.get('agence')
            structure_id = request.POST.get('structure')
            date_val = request.POST.get('date')

            if not all([type_support, agence_id, structure_id, date_val]):
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
                return redirect('realisation_detail', pk=pk)

            try:
                realisation.type_support = type_support
                realisation.agence = Agence.objects.get(id=agence_id)
                realisation.structure = Structure.objects.get(id=structure_id)
                realisation.date = date_val

                if request.FILES.get('image'):
                    realisation.image = request.FILES.get('image')

                realisation.save()

                for rl in realisation.langues.all():
                    nouvelle_qte = request.POST.get(f'langue_qte_{rl.id}')
                    if nouvelle_qte:
                        try:
                            nouvelle_qte = int(nouvelle_qte)
                            if nouvelle_qte >= rl.quantite_distribuee:
                                rl.quantite = nouvelle_qte
                                rl.save()
                            else:
                                messages.warning(
                                    request,
                                    f"Quantité en {rl.langue.nom} non modifiée : "
                                    f"{rl.quantite_distribuee} unité(s) déjà distribuée(s)."
                                )
                        except ValueError:
                            pass

                messages.success(request, "Réalisation modifiée avec succès !")
            except Exception as e:
                messages.error(request, f"Erreur lors de la modification : {e}")
            return redirect('realisation_detail', pk=pk)

        # ── FORMULAIRE : ++ disrtribution bouton dans acceuil ──
        elif form_type == 'distribution':
            evenement_id = request.POST.get('dist_evenement')
            date_val = request.POST.get('dist_date')

            if not evenement_id or not date_val:
                messages.error(request, "Veuillez choisir un événement et une date.")
                return redirect('realisation_detail', pk=pk)

            try:
                evenement_obj = Evenement.objects.get(id=evenement_id)

                # Le lieu de la distribution est place automatiquement du lieu de l evnmt
                lieu_obj, _ = Lieu.objects.get_or_create(nom=evenement_obj.lieu or "Non précisé")

                nb_ajoutees = 0
                erreurs = []
                for rl in realisation.langues.all():
                    qte_str = request.POST.get(f'dist_qte_{rl.langue.id}', '').strip()
                    if qte_str:
                        try:
                            qte = int(qte_str)
                            if qte <= 0:
                                continue
                            distribution = Distribution(
                                realisation=realisation,
                                lieu=lieu_obj,
                                langue=rl.langue,
                                evenement=evenement_obj,
                                quantite=qte,
                                date=date_val,
                                cree_par=request.user,
                            )
                            distribution.full_clean()
                            distribution.save()
                            nb_ajoutees += 1
                        except ValidationError as e:
                            erreurs.append(f"{rl.langue.nom} : {' '.join(e.messages)}")
                        except ValueError:
                            erreurs.append(f"{rl.langue.nom} : quantité invalide.")

                if nb_ajoutees:
                    messages.success(request, f"{nb_ajoutees} distribution(s) enregistrée(s) pour « {evenement_obj.titre} » !")
                if erreurs:
                    messages.warning(request, " | ".join(erreurs))
                if not nb_ajoutees and not erreurs:
                    messages.error(request, "Aucune quantité indiquée.")
            except Evenement.DoesNotExist:
                messages.error(request, "Événement introuvable.")
            except Exception as e:
                messages.error(request, f"Erreur : {e}")
            return redirect('realisation_detail', pk=pk)

    context = {
        'realisation': realisation,
        'agences': Agence.objects.all().order_by('nom'),
        'structures': Structure.objects.all().order_by('nom'),
        'type_choices': Realisation.TYPE_SUPPORT_CHOICES,
        'lieux': Lieu.objects.all().order_by('nom'),
        'distributions': realisation.distributions.select_related('lieu', 'langue').order_by('-date'),
        'evenements': Evenement.objects.filter(action=realisation.action).order_by('-date_debut'),
    }
    return render(request, 'gestion/realisation_detail.html', context)


@login_required(login_url='login')
def evenement_list(request):
    evenements = Evenement.objects.select_related('action').prefetch_related('images').order_by('-date_debut')

    evenements_geo_data = []
    for ev in evenements:
        if ev.latitude and ev.longitude:
            evenements_geo_data.append({
                'id': ev.id,
                'titre': ev.titre,
                'lieu': ev.lieu,
                'lat': ev.latitude,
                'lon': ev.longitude,
                'action': ev.action.nom,
            })

    evenements_data = []
    for ev in evenements:
        evenements_data.append({
            'id': ev.id,
            'titre': ev.titre,
            'lieu': ev.lieu or 'Non précisé',
            'action': ev.action.nom,
            'date_debut': ev.date_debut.strftime('%d/%m/%Y') if ev.date_debut else '',
            'date_fin': ev.date_fin.strftime('%d/%m/%Y') if ev.date_fin else '',
            'images': [img.image.url for img in ev.images.all()],
        })

    context = {
        'evenements': evenements,
        'evenements_geo_json': json.dumps(evenements_geo_data),
        'evenements_data_json': json.dumps(evenements_data),
    }
    return render(request, 'gestion/evenement_list.html', context)


@login_required(login_url='login')
def evenement_edit(request, pk):
    evenement = get_object_or_404(Evenement.objects.prefetch_related('images'), pk=pk)

    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        lieu = request.POST.get('lieu', '').strip()
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin') or None

        if not titre or not date_debut:
            messages.error(request, "Le titre et la date de début sont obligatoires.")
            return redirect('evenement_edit', pk=pk)

        try:
            lieu_change = lieu != evenement.lieu
            evenement.titre = titre
            evenement.date_debut = date_debut
            evenement.date_fin = date_fin

            if lieu_change:
                lat, lon = geocode_lieu(lieu)
                evenement.lieu = lieu
                evenement.latitude = lat
                evenement.longitude = lon

            evenement.save()

            # photo coche supprime
            delete_ids = request.POST.getlist('delete_images')
            if delete_ids:
                EvenementImage.objects.filter(id__in=delete_ids, evenement=evenement).delete()

            # ++nvl photo
            nouvelles_images = request.FILES.getlist('nouvelles_images')
            ordre_depart = evenement.images.count()
            for idx, img in enumerate(nouvelles_images):
                EvenementImage.objects.create(evenement=evenement, image=img, ordre=ordre_depart + idx)

            messages.success(request, "Événement modifié avec succès !")
            if request.user.is_admin_role():
                return redirect('admin_evenements')
            return redirect('evenement_list')
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {e}")
            return redirect('evenement_edit', pk=pk)

    return render(request, 'gestion/evenement_edit.html', {'evenement': evenement})
# ═══════════════════════════════════════════════════════
# ESPACE ADMINISTRATEUR
# ═══════════════════════════════════════════════════════


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_role():
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    total_realisations = Realisation.objects.count()
    total_evenements = Evenement.objects.count()
    total_users = Utilisateur.objects.count()
    total_agences = Agence.objects.count()

    total_quantite = RealisationLangue.objects.aggregate(Sum('quantite'))['quantite__sum'] or 0
    total_distribue = Distribution.objects.aggregate(Sum('quantite'))['quantite__sum'] or 0
    total_reste = total_quantite - total_distribue

    stats_statut = {'vert': 0, 'orange': 0, 'rouge': 0}
    for r in Realisation.objects.all():
        stats_statut[r.statut_distribution] += 1

    dernieres_realisations = Realisation.objects.select_related('action', 'agence').order_by('-date')[:5]

    context = {
        'active': 'dashboard',
        'total_realisations': total_realisations,
        'total_evenements': total_evenements,
        'total_users': total_users,
        'total_agences': total_agences,
        'total_quantite': total_quantite,
        'total_distribue': total_distribue,
        'total_reste': total_reste,
        'stats_statut': stats_statut,
        'dernieres_realisations': dernieres_realisations,
    }
    return render(request, 'gestion/admin/dashboard.html', context)


@admin_required
def admin_users(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            role = request.POST.get('role', 'user')
            email = request.POST.get('email', '').strip()

            if not username or not password:
                messages.error(request, "Nom d'utilisateur et mot de passe obligatoires.")
            elif Utilisateur.objects.filter(username=username).exists():
                messages.error(request, "Ce nom d'utilisateur existe déjà.")
            else:
                nouvel_user = Utilisateur.objects.create_user(username=username, password=password, email=email)
                nouvel_user.role = role
                nouvel_user.save()
                messages.success(request, f"Utilisateur « {username} » créé avec succès.")

        elif action == 'delete':
            user_id = request.POST.get('user_id')
            if str(request.user.id) == user_id:
                messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
            else:
                Utilisateur.objects.filter(id=user_id).delete()
                messages.success(request, "Utilisateur supprimé.")

        return redirect('admin_users')

    query = request.GET.get('q', '').strip()
    users = Utilisateur.objects.all().order_by('username')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    return render(request, 'gestion/admin/users.html', {'active': 'users', 'users': users, 'query': query})
@admin_required
def admin_user_edit(request, pk):
    edited_user = get_object_or_404(Utilisateur, pk=pk)

    if request.method == 'POST':
        edited_user.username = request.POST.get('username', edited_user.username).strip()
        edited_user.email = request.POST.get('email', '').strip()
        edited_user.role = request.POST.get('role', edited_user.role)

        new_password = request.POST.get('password', '').strip()
        if new_password:
            edited_user.set_password(new_password)

        edited_user.save()
        messages.success(request, "Utilisateur modifié avec succès.")
        return redirect('admin_users')

    return render(request, 'gestion/admin/user_edit.html', {'active': 'users', 'edited_user': edited_user})


@admin_required
def admin_agences_structures(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_agence':
            nom = request.POST.get('nom_agence', '').strip()
            if nom:
                Agence.objects.get_or_create(nom=nom)
                messages.success(request, "Agence ajoutée.")

        elif action == 'delete_agence':
            Agence.objects.filter(id=request.POST.get('agence_id')).delete()
            messages.success(request, "Agence supprimée.")

        elif action == 'add_structure':
            nom = request.POST.get('nom_structure', '').strip()
            if nom:
                Structure.objects.get_or_create(nom=nom)
                messages.success(request, "Structure ajoutée.")

        elif action == 'delete_structure':
            Structure.objects.filter(id=request.POST.get('structure_id')).delete()
            messages.success(request, "Structure supprimée.")

        return redirect('admin_agences_structures')

    context = {
        'active': 'agences',
        'agences': Agence.objects.all().order_by('nom'),
        'structures': Structure.objects.all().order_by('nom'),
    }
    return render(request, 'gestion/admin/agences_structures.html', context)


@admin_required
def admin_settings(request):
    if request.method == 'POST':
        request.user.username = request.POST.get('username', request.user.username).strip()
        request.user.email = request.POST.get('email', '').strip()

        if request.FILES.get('photo'):
            request.user.photo = request.FILES.get('photo')

        new_password = request.POST.get('password', '').strip()
        if new_password:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
        else:
            request.user.save()

        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('admin_settings')

    return render(request, 'gestion/admin/settings.html', {'active': 'settings'})


@admin_required
def admin_profile(request):
    return render(request, 'gestion/admin/profile.html', {'active': 'profile'})


@admin_required
def admin_generate_pdf(request):
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from django.http import HttpResponse
    from django.utils import timezone

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    orange = colors.HexColor('#f5821f')

    title_style = ParagraphStyle('TitleOrange', parent=styles['Title'], textColor=orange, fontSize=20)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], textColor=colors.grey, fontSize=9)

    story = [
        Paragraph("Naftal GPL — Rapport Statistique des Réalisations", title_style),
        Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}", sub_style),
        Spacer(1, 20),
    ]

    realisations = Realisation.objects.select_related('agence', 'action', 'structure').order_by('-date')
    data = [['Action', 'Type', 'Agence', 'Total', 'Distribué', 'Reste', 'Statut']]
    for r in realisations:
        data.append([
            r.action.nom[:28], r.get_type_support_display(), r.agence.nom[:20],
            str(r.quantite_globale), str(r.quantite_distribuee_globale),
            str(r.reste_global), r.statut_label,
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff4ec')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_naftal_gpl.pdf"'
    return response
# ═══════════════════════════════════════════════════════
# ici admin qui est moi gere action event suppr ett
# ═══════════════════════════════════════════════════════

@admin_required
def admin_realisations(request):
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        Realisation.objects.filter(id=request.POST.get('realisation_id')).delete()
        messages.success(request, "Réalisation supprimée.")
        return redirect('admin_realisations')

    query = request.GET.get('q', '').strip()
    realisations = Realisation.objects.select_related('action', 'agence', 'structure').order_by('-date')
    if query:
        realisations = realisations.filter(
            Q(action__nom__icontains=query) |
            Q(type_support__icontains=query) |
            Q(structure__nom__icontains=query) |
            Q(agence__nom__icontains=query)
        )

    context = {'active': 'realisations', 'realisations': realisations, 'query': query}
    return render(request, 'gestion/admin/realisations.html', context)


@admin_required
def admin_evenements(request):
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        Evenement.objects.filter(id=request.POST.get('evenement_id')).delete()
        messages.success(request, "Événement supprimé.")
        return redirect('admin_evenements')

    query = request.GET.get('q', '').strip()
    evenements = Evenement.objects.select_related('action').order_by('-date_debut')
    if query:
        evenements = evenements.filter(
            Q(titre__icontains=query) |
            Q(lieu__icontains=query) |
            Q(action__nom__icontains=query)
        )

    context = {'active': 'evenements', 'evenements': evenements, 'query': query}
    return render(request, 'gestion/admin/evenements.html', context)


@admin_required
def admin_actions(request):
    if request.method == 'POST':
        act = request.POST.get('action')

        if act == 'create':
            nom = request.POST.get('nom_action', '').strip()
            desc = request.POST.get('description_action', '').strip()
            if nom:
                Action.objects.get_or_create(nom=nom, defaults={'description': desc})
                messages.success(request, "Action créée.")

        elif act == 'edit':
            a = Action.objects.filter(id=request.POST.get('action_id')).first()
            if a:
                a.nom = request.POST.get('nom_action', a.nom).strip()
                a.description = request.POST.get('description_action', a.description).strip()
                a.save()
                messages.success(request, "Action modifiée.")

        elif act == 'delete':
            Action.objects.filter(id=request.POST.get('action_id')).delete()
            messages.success(request, "Action supprimée.")

        return redirect('admin_actions')

    query = request.GET.get('q', '').strip()
    actions = Action.objects.all().order_by('nom')
    if query:
        actions = actions.filter(nom__icontains=query)

    context = {'active': 'actions', 'actions': actions, 'query': query}
    return render(request, 'gestion/admin/actions.html', context)
@login_required(login_url='login')
def statistiques_parametres(request):
    """Page où l'utilisateur choisit les filtres avant de générer le PDF."""
    context = {
        'actions': Action.objects.all().order_by('nom'),
        'lieux': Lieu.objects.all().order_by('nom'),
        'annees': Realisation.objects.dates('date', 'year', order='DESC'),
    }
    return render(request, 'gestion/statistiques_parametres.html', context)
 
 
@login_required(login_url='login')
def generer_pdf_stats(request):
    if request.method != 'POST':
        return redirect('statistiques_parametres')
 
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from django.http import HttpResponse
    from django.utils import timezone
 
    # ── FILTRES (inchangé) ──
    annee = request.POST.get('annee', '').strip()
    mois = request.POST.get('mois', '').strip()
    tous_lieux = request.POST.get('tous_lieux') == 'on'
    tous_actions = request.POST.get('tous_actions') == 'on'
    lieu_ids = [] if tous_lieux else request.POST.getlist('lieux')
    action_ids = [] if tous_actions else request.POST.getlist('actions')
    inclure_stats = request.POST.get('stats_generales') == 'on'
    inclure_graphiques = request.POST.get('graphiques') == 'on'
 
    realisations = Realisation.objects.select_related(
        'agence', 'action', 'structure'
    ).prefetch_related('langues__langue')
    distributions = Distribution.objects.select_related('lieu', 'langue', 'realisation__action')
 
    if annee:
        realisations = realisations.filter(date__year=annee)
        distributions = distributions.filter(date__year=annee)
    if mois:
        realisations = realisations.filter(date__month=mois)
        distributions = distributions.filter(date__month=mois)
    if action_ids:
        realisations = realisations.filter(action__id__in=action_ids)
        distributions = distributions.filter(realisation__action__id__in=action_ids)
    if lieu_ids:
        distributions = distributions.filter(lieu__id__in=lieu_ids)
 
    realisations = realisations.order_by('-date').distinct()
 
    # ── PALETTE PROFESSIONNELLE
    noir = colors.HexColor('#000000')
    gris_fonce = colors.HexColor('#2b2b2b')
    gris_moyen = colors.HexColor('#6b6b6b')
    gris_clair = colors.HexColor('#f2f2f2')
    gris_ligne = colors.HexColor('#bfbfbf')
 
    date_generation = timezone.now()
 
    # ── EN-TÊTE / PIED DE PAGE 
    def entete_pied_de_page(canvas, doc):
        canvas.saveState()
        largeur, hauteur = A4
 
        # Bloc identité (haut gauche) + date (haut droite)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(noir)
        canvas.drawString(2 * cm, hauteur - 1.4 * cm, "NAFTAL — GPL")
 
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(gris_moyen)
        canvas.drawString(2 * cm, hauteur - 1.85 * cm, "Rapport statistique interne")
 
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(noir)
        canvas.drawRightString(largeur - 2 * cm, hauteur - 1.4 * cm,
                                date_generation.strftime('%d/%m/%Y — %H:%M'))
 
        # Filet horizontal sous l'en-tête
        canvas.setStrokeColor(noir)
        canvas.setLineWidth(1)
        canvas.line(2 * cm, hauteur - 2.1 * cm, largeur - 2 * cm, hauteur - 2.1 * cm)
 
        # Pied de page : filet + numéro de page
        canvas.setStrokeColor(gris_ligne)
        canvas.setLineWidth(0.6)
        canvas.line(2 * cm, 1.6 * cm, largeur - 2 * cm, 1.6 * cm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(gris_moyen)
        canvas.drawCentredString(largeur / 2, 1.15 * cm, f"Page {doc.page}")
        canvas.drawString(2 * cm, 1.15 * cm, "Naftal GPL — Document à usage interne")
 
        canvas.restoreState()
 
    # ── DOCUMENT ──
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2.9 * cm, bottomMargin=2.2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
 
    title_style = ParagraphStyle(
        'Titre', parent=styles['Title'], textColor=noir,
        fontName='Helvetica-Bold', fontSize=18, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        'Sous-titre', parent=styles['Normal'], textColor=gris_moyen, fontSize=9
    )
    # Style de titre de section, avec puce carrée façon rapport officiel
    h2_style = ParagraphStyle(
        'Section', parent=styles['Heading2'], textColor=noir,
        fontName='Helvetica-Bold', fontSize=13, spaceBefore=20, spaceAfter=10,
        leading=16,
    )
 
    def titre_section(texte):
        # ▪ = puce carrée noire devant chaque titre de section
        return Paragraph(f"▪&nbsp;&nbsp;{texte}", h2_style)
 
    filtres_txt = []
    if annee: filtres_txt.append(f"Année {annee}")
    if mois: filtres_txt.append(f"Mois {mois}")
    if action_ids: filtres_txt.append(f"{len(action_ids)} action(s)")
    if lieu_ids: filtres_txt.append(f"{len(lieu_ids)} lieu(x)")
    filtres_str = " • ".join(filtres_txt) if filtres_txt else "Toutes les données"
 
    story = [
        Paragraph("RAPPORT STATISTIQUE", title_style),
        Paragraph(f"Filtres appliqués : {filtres_str}", sub_style),
        Spacer(1, 22),
    ]
 
    style_table_entete = ('BACKGROUND', (0, 0), (-1, 0), noir)
    style_table_texte_entete = ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
    style_table_bandes = ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_clair])
    style_table_grille = ('GRID', (0, 0), (-1, -1), 0.5, gris_ligne)
 
    # ── STATISTIQUES General
    if inclure_stats:
        total_realise = RealisationLangue.objects.filter(
            realisation__in=realisations
        ).aggregate(Sum('quantite'))['quantite__sum'] or 0
        total_distribue = distributions.aggregate(Sum('quantite'))['quantite__sum'] or 0
        total_reste = total_realise - total_distribue
 
        story.append(titre_section("Statistiques générales"))
        data_gen = [
            ['Indicateur', 'Valeur'],
            ['Réalisations concernées', str(realisations.count())],
            ['Unités réalisées', str(total_realise)],
            ['Unités distribuées', str(total_distribue)],
            ['Unités restantes', str(total_reste)],
        ]
        t = Table(data_gen, colWidths=[10 * cm, 6 * cm])
        t.setStyle(TableStyle([
            style_table_entete, style_table_texte_entete,
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            style_table_grille, style_table_bandes,
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
 
        langues_data = RealisationLangue.objects.filter(
            realisation__in=realisations
        ).values('langue__nom').annotate(total=Sum('quantite')).order_by('-total')
        if langues_data:
            story.append(titre_section("Quantités réalisées par langue"))
            data_langues = [['Langue', 'Quantité réalisée']]
            for row in langues_data:
                data_langues.append([row['langue__nom'], str(row['total'])])
            t2 = Table(data_langues, colWidths=[10 * cm, 6 * cm])
            t2.setStyle(TableStyle([
                style_table_entete, style_table_texte_entete,
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                style_table_grille, style_table_bandes,
            ]))
            story.append(t2)
            story.append(Spacer(1, 12))
 
    # si user choisi d ajouter grzaphics
    if inclure_graphiques:
        story.append(titre_section("Représentation graphique"))
 
        nuances_gris = [gris_fonce, gris_moyen, colors.HexColor('#a6a6a6'),
                         colors.HexColor('#d9d9d9'), noir, colors.HexColor('#8c8c8c')]
 
        stats_statut = {'vert': 0, 'orange': 0, 'rouge': 0}
        for r in realisations:
            stats_statut[r.statut_distribution] += 1
        valeurs = [(k, v) for k, v in stats_statut.items() if v > 0]
 
        if valeurs:
            d1 = Drawing(400, 200)
            pie1 = Pie()
            pie1.x, pie1.y, pie1.width, pie1.height = 100, 25, 140, 140
            pie1.data = [v for _, v in valeurs]
            pie1.labels = [f"{k} ({v})" for k, v in valeurs]
            pie1.slices.strokeWidth = 1
            pie1.slices.strokeColor = colors.white
            for i, _ in enumerate(valeurs):
                pie1.slices[i].fillColor = nuances_gris[i % len(nuances_gris)]
            d1.add(pie1)
            story.append(Paragraph("Statut des réalisations (disponible / faible / épuisé)", styles['Normal']))
            story.append(d1)
            story.append(Spacer(1, 12))
 
        langues_dist = distributions.values('langue__nom').annotate(total=Sum('quantite')).order_by('-total')
        if langues_dist:
            d2 = Drawing(400, 200)
            pie2 = Pie()
            pie2.x, pie2.y, pie2.width, pie2.height = 100, 25, 140, 140
            pie2.data = [row['total'] for row in langues_dist]
            pie2.labels = [f"{row['langue__nom'] or 'N/A'} ({row['total']})" for row in langues_dist]
            pie2.slices.strokeWidth = 1
            pie2.slices.strokeColor = colors.white
            for idx in range(len(langues_dist)):
                pie2.slices[idx].fillColor = nuances_gris[idx % len(nuances_gris)]
            d2.add(pie2)
            story.append(Paragraph("Répartition des unités distribuées par langue", styles['Normal']))
            story.append(d2)
            story.append(Spacer(1, 12))
 
    # detail realisations
    story.append(PageBreak())
    story.append(titre_section("Détail des réalisations"))
    data = [['Action', 'Type', 'Agence', 'Total', 'Distribué', 'Reste', 'Statut']]
    for r in realisations:
        data.append([
            r.action.nom[:28], r.get_type_support_display(), r.agence.nom[:20],
            str(r.quantite_globale), str(r.quantite_distribuee_globale),
            str(r.reste_global), r.statut_label,
        ])
    if len(data) == 1:
        data.append(['Aucune donnée pour ces filtres', '', '', '', '', '', ''])
 
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        style_table_entete, style_table_texte_entete,
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        style_table_grille, style_table_bandes,
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
 
    
    doc.build(story, onFirstPage=entete_pied_de_page, onLaterPages=entete_pied_de_page)
 
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_naftal_gpl.pdf"'
    return response