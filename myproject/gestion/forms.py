from django import forms
from .models import Realisation, Evenement, RealisationLangue


class ActionEvenementForm(forms.Form):
    """Formulaire pour créer une Action + ses Événements en même temps"""
    action_nom = forms.CharField(
        max_length=200,
        label="Nom de l'action",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Campagne hivernale 2024'})
    )
    action_description = forms.CharField(
        required=False,
        label="Description (optionnel)",
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2})
    )


class EvenementForm(forms.ModelForm):
    class Meta:
        model = Evenement
        fields = ['titre', 'lieu', 'date_debut', 'date_fin']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Foire internationale'}),
            'lieu': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Palais des Expositions, Alger'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }
        labels = {
            'titre': 'Titre de l\'événement',
            'lieu': 'Lieu',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin (optionnel)',
        }


class RealisationForm(forms.ModelForm):
    class Meta:
        model = Realisation
        fields = ['type_support', 'agence', 'action', 'structure', 'date']
        widgets = {
            'type_support': forms.Select(attrs={'class': 'form-input'}),
            'agence': forms.Select(attrs={'class': 'form-input'}),
            'action': forms.Select(attrs={'class': 'form-input'}),
            'structure': forms.Select(attrs={'class': 'form-input'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }
        labels = {
            'type_support': 'Type de support',
            'agence': 'Agence retenue',
            'action': 'Action / Campagne',
            'structure': 'Structure demandeuse',
            'date': 'Date de réalisation',
        }


class RealisationLangueForm(forms.ModelForm):
    """Un formulaire par langue ajoutée dynamiquement"""
    class Meta:
        model = RealisationLangue
        fields = ['langue', 'quantite']
        widgets = {
            'langue': forms.Select(attrs={'class': 'form-input'}),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'placeholder': 'Quantité'
            }),
        }
        labels = {
            'langue': 'Langue',
            'quantite': 'Quantité',
        }