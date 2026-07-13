from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('user', 'Utilisateur'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    photo = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_admin_role(self):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.username} ({self.role})"

# ---------------------------------------------------------
# REFERENCE TABLES
# ---------------------------------------------------------

class Agence(models.Model):
    nom = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Agence"
        verbose_name_plural = "Agences"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Action(models.Model):
    # Action = description de travail en general une peu contneir plusieur event
    # Pas de dates ici — les dates sont sur les Evnt
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Action"
        verbose_name_plural = "Actions"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Evenement(models.Model):
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, related_name='evenements'
    )
    titre = models.CharField(max_length=200)
    lieu = models.CharField(max_length=200, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.titre} ({self.action.nom})"


class Structure(models.Model):
    nom = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Structure"
        verbose_name_plural = "Structures"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Langue(models.Model):
    nom = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Langue"
        verbose_name_plural = "Langues"

    def __str__(self):
        return self.nom


class Lieu(models.Model):
    TYPE_CHOICES = [
        ('station', 'Station-service'),
        ('wilaya', 'Wilaya'),
        ('district', 'District'),
    ]
    nom = models.CharField(max_length=150)
    type_lieu = models.CharField(max_length=20, choices=TYPE_CHOICES, default='station')

    class Meta:
        verbose_name = "Lieu"
        verbose_name_plural = "Lieux"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_lieu_display()})"


# ---------------------------------------------------------
# les tbles de mon core busnies
# ---------------------------------------------------------

class Realisation(models.Model):
    TYPE_SUPPORT_CHOICES = [
        ('affiche', 'Affiche'),
        ('depliant', 'Dépliant'),
        ('prospectus', 'Prospectus'),
        ('guide', 'Guide'),
        ('panneau', 'Panneau'),
        ('autre', 'Autre'),
    ]
    image = models.ImageField(
        upload_to='realisations/',
        blank=True,
        null=True
    )
    type_support = models.CharField(max_length=20, choices=TYPE_SUPPORT_CHOICES)
    agence = models.ForeignKey(
        Agence, on_delete=models.PROTECT, related_name='realisations'
    )
    action = models.ForeignKey(
        Action, on_delete=models.PROTECT, related_name='realisations'
    )
    structure = models.ForeignKey(
        Structure, on_delete=models.PROTECT, related_name='realisations'
    )

    date = models.DateField()
    cree_par = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='realisations_creees'
    )

    class Meta:
        verbose_name = "Réalisation"
        verbose_name_plural = "Réalisations"
        ordering = ['-date']

    def __str__(self):
        return f"{self.get_type_support_display()} — {self.action.nom}"

    @property
    def quantite_globale(self):
        # Somme de toutes les langues n est pas stocke fiffffiiiii
        total = self.langues.aggregate(models.Sum('quantite'))['quantite__sum']
        return total or 0

    @property
    def quantite_distribuee_globale(self):
        total = self.distributions.aggregate(models.Sum('quantite'))['quantite__sum']
        return total or 0

    @property
    def reste_global(self):
        return self.quantite_globale - self.quantite_distribuee_globale
    @property
    def pourcentage_restant(self):
        total = self.quantite_globale
        if total == 0:
            return 0
        return round((self.reste_global / total) * 100, 1)

    @property
    def statut_distribution(self):
        pct = self.pourcentage_restant
        if pct <= 0:
            return 'rouge'
        elif pct <= 20:
            return 'orange'
        else:
            return 'vert'

    @property
    def statut_label(self):
        return {
            'rouge': 'Épuisé',
            'orange': 'Stock faible',
            'vert': 'Stock disponible',
        }[self.statut_distribution]
class RealisationLangue(models.Model):
    # Une ligne = une langue + sa quantité pour une réalisation donnée
    # faut penser a affichage
    realisation = models.ForeignKey(
        Realisation, on_delete=models.CASCADE, related_name='langues'
    )
    langue = models.ForeignKey(
        Langue, on_delete=models.PROTECT, related_name='realisation_langues'
    )
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Quantité par langue"
        verbose_name_plural = "Quantités par langue"
        # pour ne pas avoir deux fois la meme langue pour une realisation
        unique_together = [['realisation', 'langue']]

    def __str__(self):
        return f"{self.langue.nom}: {self.quantite}"

    @property
    def quantite_distribuee(self):
        total = Distribution.objects.filter(
            realisation=self.realisation,
            langue=self.langue
        ).aggregate(models.Sum('quantite'))['quantite__sum']
        return total or 0

    @property
    def reste(self):
        return self.quantite - self.quantite_distribuee


class Distribution(models.Model):
    realisation = models.ForeignKey(
        Realisation, on_delete=models.CASCADE, related_name='distributions'
    )
    lieu = models.ForeignKey(
        Lieu, on_delete=models.PROTECT, related_name='distributions'
    )
    langue = models.ForeignKey(
        Langue, on_delete=models.PROTECT, related_name='distributions',
        null=True, blank=True
        # langue ici pour savoir exactement combien de chaque langue ete distribuee
    ) 
    evenement = models.ForeignKey(
        Evenement, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='distributions'
    )
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    date = models.DateField()
    cree_par = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='distributions_creees'
    )
   

    class Meta:
        verbose_name = "Distribution"
        verbose_name_plural = "Distributions"
        ordering = ['-date']

    def __str__(self):
        return f"{self.realisation} → {self.lieu} : {self.quantite}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.langue:
            return
        # Vérifier qu  on ne distribue pas plus que le reste pour cette langue
        rl = RealisationLangue.objects.filter(
            realisation=self.realisation,
            langue=self.langue
        ).first()
        if not rl:
            raise ValidationError("Cette langue n'existe pas pour cette réalisation.")
        deja = Distribution.objects.filter(
            realisation=self.realisation,
            langue=self.langue
        ).exclude(pk=self.pk).aggregate(
            models.Sum('quantite')
        )['quantite__sum'] or 0
        disponible = rl.quantite - deja
        if self.quantite > disponible:
            raise ValidationError(
                f"Quantité trop élevée. Il ne reste que {disponible} en {self.langue.nom}."
            )
class EvenementImage(models.Model):
    evenement = models.ForeignKey(
        Evenement, on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='evenements/')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Image événement"