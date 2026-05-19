from django.db import models
from django.utils import timezone


class CalculHistorique(models.Model):
    montant = models.FloatField()
    taux = models.FloatField()
    type_taux = models.CharField(max_length=10)  # 'annuel' ou 'mensuel'
    duree = models.IntegerField()
    valeur_actuelle = models.FloatField()
    interets_totaux = models.FloatField()
    date_calcul = models.DateTimeField(default=timezone.now)
    email_envoye = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.montant}€ - {self.date_calcul.strftime('%d/%m/%Y %H:%M')}"