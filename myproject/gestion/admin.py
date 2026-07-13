from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Utilisateur, Agence, Action, Evenement, EvenementImage,
    Structure, Langue, Lieu, Realisation, RealisationLangue, Distribution
)


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Rôle', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')


# ---------------------------------------------------------
# REFERENCE TABLES
# ---------------------------------------------------------

@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


class EvenementImageInline(admin.TabularInline):
    model = EvenementImage
    extra = 1
    fields = ('image', 'ordre')


class EvenementInline(admin.StackedInline):
    model = Evenement
    extra = 1
    fields = ('titre', 'lieu', 'date_debut', 'date_fin')
    show_change_link = True


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)
    inlines = [EvenementInline]


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ('titre', 'action', 'lieu', 'date_debut', 'date_fin')
    list_filter = ('date_debut',)
    search_fields = ('titre', 'action__nom')
    inlines = [EvenementImageInline]


@admin.register(EvenementImage)
class EvenementImageAdmin(admin.ModelAdmin):
    list_display = ('evenement', 'ordre')


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(Langue)
class LangueAdmin(admin.ModelAdmin):
    list_display = ('nom',)


@admin.register(Lieu)
class LieuAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_lieu')
    list_filter = ('type_lieu',)
    search_fields = ('nom',)


# ---------------------------------------------------------
# CORE BUSINESS TABLES
# ---------------------------------------------------------

class RealisationLangueInline(admin.TabularInline):
    model = RealisationLangue
    extra = 1
    fields = ('langue', 'quantite')


class DistributionInline(admin.TabularInline):
    model = Distribution
    extra = 1
    fields = ('lieu', 'langue', 'quantite', 'date', 'cree_par')


@admin.register(Realisation)
class RealisationAdmin(admin.ModelAdmin):
    list_display = (
        'type_support', 'action', 'agence',
        'structure', 'quantite_globale', 'quantite_distribuee_globale',
        'reste_global', 'date'
    )
    list_filter = ('type_support', 'action', 'structure', 'date')
    search_fields = ('action__nom', 'structure__nom', 'agence__nom')
    inlines = [RealisationLangueInline, DistributionInline]

    def quantite_globale(self, obj):
        return obj.quantite_globale
    quantite_globale.short_description = 'Qté Globale'

    def quantite_distribuee_globale(self, obj):
        return obj.quantite_distribuee_globale
    quantite_distribuee_globale.short_description = 'Distribué'

    def reste_global(self, obj):
        return obj.reste_global
    reste_global.short_description = 'Reste'


@admin.register(RealisationLangue)
class RealisationLangueAdmin(admin.ModelAdmin):
    list_display = ('realisation', 'langue', 'quantite', 'quantite_distribuee', 'reste')
    list_filter = ('langue',)

    def quantite_distribuee(self, obj):
        return obj.quantite_distribuee
    quantite_distribuee.short_description = 'Distribué'

    def reste(self, obj):
        return obj.reste
    reste.short_description = 'Reste'


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ('realisation', 'lieu', 'langue', 'quantite', 'date', 'cree_par')
    list_filter = ('lieu', 'langue', 'date')
    search_fields = ('realisation__action__nom', 'lieu__nom')