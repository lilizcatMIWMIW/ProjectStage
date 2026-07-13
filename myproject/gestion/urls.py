from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.connexion_view, name='login'),
    path('logout/', views.deconnexion_view, name='logout'),
    path('', views.home, name='home'),
    path('realisations/', views.realisation_list, name='realisation_list'),
    path('realisations/creer/', views.realisation_create, name='realisation_create'),
    path('realisations/<int:pk>/', views.realisation_detail, name='realisation_detail'),
    path('evenements/', views.evenement_list, name='evenement_list'),
    path('evenements/<int:pk>/modifier/', views.evenement_edit, name='evenement_edit'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
path('admin-panel/utilisateurs/', views.admin_users, name='admin_users'),
path('admin-panel/utilisateurs/<int:pk>/modifier/', views.admin_user_edit, name='admin_user_edit'),
path('admin-panel/agences-structures/', views.admin_agences_structures, name='admin_agences_structures'),
path('admin-panel/parametres/', views.admin_settings, name='admin_settings'),
path('admin-panel/profil/', views.admin_profile, name='admin_profile'),
path('admin-panel/rapport-pdf/', views.admin_generate_pdf, name='admin_generate_pdf'),
path('admin-panel/realisations/', views.admin_realisations, name='admin_realisations'),
path('admin-panel/evenements/', views.admin_evenements, name='admin_evenements'),
path('admin-panel/actions/', views.admin_actions, name='admin_actions'),
    path('statistiques/', views.statistiques_parametres, name='statistiques_parametres'),
path('statistiques/pdf/', views.generer_pdf_stats, name='generer_pdf_stats'),
]