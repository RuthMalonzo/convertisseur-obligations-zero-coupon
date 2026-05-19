from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from matplotlib import pyplot as plt
import matplotlib

matplotlib.use('Agg')  # Pour éviter les problèmes d'affichage
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from .models import CalculHistorique
import tempfile
import os


def generer_graphique(tableau, label_periode):
    """Génère un graphique des intérêts"""
    periodes = [ligne['periode'] for ligne in tableau]
    interets = [ligne['interet'] for ligne in tableau]

    plt.figure(figsize=(10, 6))
    plt.plot(periodes, interets, marker='o', linewidth=2, markersize=6, color='#667eea')
    plt.fill_between(periodes, interets, alpha=0.3, color='#667eea')
    plt.title(f'Évolution des intérêts par {label_periode}', fontsize=14, fontweight='bold')
    plt.xlabel(f'{label_periode}', fontsize=12)
    plt.ylabel('Intérêts (€)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(periodes)

    # Convertir en base64 pour l'affichage HTML
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"


def generer_pdf(resultats, tableau, label_periode):
    """Génère un PDF avec les résultats"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Titre
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "Rapport de Conversion d'Obligations")

    # Informations générales
    p.setFont("Helvetica", 12)
    y = height - 100
    p.drawString(50, y, f"Montant nominal: {resultats['montant']} €")
    p.drawString(50, y - 25, f"Taux d'intérêt: {resultats['taux']}% ({resultats['type_taux']})")
    p.drawString(50, y - 50, f"Durée: {resultats['duree']} {label_periode}")
    p.drawString(50, y - 75, f"Valeur actuelle (Zéro Coupon): {resultats['valeur_actuelle']} €")
    p.drawString(50, y - 100, f"Intérêts totaux: {resultats['interets_totaux']} €")

    # Tableau des résultats
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y - 150, f"Détail {label_periode} par {label_periode}:")

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y - 175, label_periode)
    p.drawString(150, y - 175, "Capital début (€)")
    p.drawString(300, y - 175, "Intérêts (€)")
    p.drawString(450, y - 175, "Capital fin (€)")

    p.setFont("Helvetica", 9)
    y_pos = y - 195
    for ligne in tableau[:20]:  # Limite à 20 lignes pour le PDF
        p.drawString(50, y_pos, str(ligne['periode']))
        p.drawString(150, y_pos, str(ligne['capital_debut']))
        p.drawString(300, y_pos, str(ligne['interet']))
        p.drawString(450, y_pos, str(ligne['capital_fin']))
        y_pos -= 20
        if y_pos < 50:
            p.showPage()
            y_pos = height - 50

    p.save()
    buffer.seek(0)
    return buffer


def calculer(request):
    contexte = {}

    if request.method == 'POST':
        try:
            montant = float(request.POST.get('montant'))
            taux = float(request.POST.get('taux')) / 100
            type_taux = request.POST.get('type_taux')
            duree = int(request.POST.get('duree'))
            email = request.POST.get('email', '')

            valeur_actuelle = montant / ((1 + taux) ** duree)
            interets_totaux = montant - valeur_actuelle

            tableau = []
            capital_acquis = valeur_actuelle

            for periode in range(1, duree + 1):
                interet_periode = capital_acquis * taux
                nouveau_capital = capital_acquis + interet_periode
                tableau.append({
                    'periode': periode,
                    'capital_debut': round(capital_acquis, 2),
                    'interet': round(interet_periode, 2),
                    'capital_fin': round(nouveau_capital, 2),
                })
                capital_acquis = nouveau_capital

            label_periode = "Année" if type_taux == "annuel" else "Mois"

            # Générer le graphique
            graphique = generer_graphique(tableau, label_periode)

            # Sauvegarder dans l'historique
            historique = CalculHistorique.objects.create(
                montant=montant,
                taux=taux * 100,
                type_taux=type_taux,
                duree=duree,
                valeur_actuelle=round(valeur_actuelle, 2),
                interets_totaux=round(interets_totaux, 2)
            )

            # Envoyer par email si demandé
            if email and email != '':
                try:
                    sujet = "Vos résultats de conversion d'obligations"
                    message = f"""
                    Bonjour,

                    Voici vos résultats de conversion :

                    Montant nominal: {montant} €
                    Taux: {taux * 100}% ({type_taux})
                    Durée: {duree} {label_periode}
                    Valeur actuelle (Zéro Coupon): {round(valeur_actuelle, 2)} €
                    Intérêts totaux: {round(interets_totaux, 2)} €

                    Consultez votre historique pour plus de détails.

                    Cordialement,
                    Votre application de conversion d'obligations
                    """
                    send_mail(
                        sujet,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    historique.email_envoye = True
                    historique.save()
                    contexte['email_envoye'] = True
                except Exception as e:
                    contexte['erreur_email'] = f"Email non envoyé: {str(e)}"

            contexte.update({
                'montant': montant,
                'taux': taux * 100,
                'type_taux': type_taux,
                'duree': duree,
                'valeur_actuelle': round(valeur_actuelle, 2),
                'interets_totaux': round(interets_totaux, 2),
                'tableau': tableau,
                'label_periode': label_periode,
                'graphique': graphique,
                'historique_id': historique.id,
                'resultat': True,
            })

            # Gérer l'export PDF
            if 'export_pdf' in request.POST:
                pdf_buffer = generer_pdf(contexte, tableau, label_periode)
                response = HttpResponse(pdf_buffer, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="conversion_obligations_{historique.id}.pdf"'
                return response

        except (ValueError, TypeError, ZeroDivisionError):
            contexte['erreur'] = "Veuillez vérifier les valeurs saisies."

    # Récupérer l'historique pour l'affichage
    contexte['historique'] = CalculHistorique.objects.all().order_by('-date_calcul')[:10]

    return render(request, 'convertisseur/index.html', contexte)


def supprimer_historique(request, id):
    """Supprimer un élément de l'historique"""
    if request.method == 'POST':
        calcul = get_object_or_404(CalculHistorique, id=id)
        calcul.delete()
    return HttpResponse(status=204)