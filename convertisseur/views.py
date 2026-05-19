from django.shortcuts import render
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
import os


# ==================== PAGES STATIQUES ====================

def produits(request):
    return render(request, 'convertisseur/produits.html')


def obligations(request):
    return render(request, 'convertisseur/obligations.html')


def contact(request):
    contexte = {}
    if request.method == 'POST':
        nom = request.POST.get('nom', '')
        email = request.POST.get('email', '')
        message = request.POST.get('message', '')
        try:
            send_mail(
                f"Message de {nom}",
                message,
                email,
                ['contact@obligations.com'],
                fail_silently=False,
            )
            contexte['message_envoye'] = True
        except:
            contexte['erreur'] = "Erreur lors de l'envoi"
    return render(request, 'convertisseur/contact.html', contexte)


# ==================== MÉTHODE SIMPLE (Zéro Coupon) ====================

def methode_simple(request):
    contexte = {}

    if request.method == 'POST' and 'export_pdf' not in request.POST:
        try:
            montant = float(request.POST.get('montant'))
            taux = float(request.POST.get('taux')) / 100
            type_taux = request.POST.get('type_taux')
            duree = int(request.POST.get('duree'))

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

            # Graphique
            periodes = [ligne['periode'] for ligne in tableau]
            interets = [ligne['interet'] for ligne in tableau]

            plt.figure(figsize=(10, 5))
            plt.bar(periodes, interets, color='#4a9eff', alpha=0.7)
            plt.plot(periodes, interets, marker='o', color='#1a2a3a', linewidth=2)
            plt.title(f'Intérêts par {label_periode}')
            plt.xlabel(label_periode)
            plt.ylabel('Intérêts (€)')
            plt.grid(True, alpha=0.3)

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            graphique = base64.b64encode(buffer.read()).decode()
            plt.close()

            # Sauvegarde en session pour l'export PDF
            request.session['resultats'] = {
                'montant': montant,
                'taux': taux * 100,
                'type_taux': type_taux,
                'duree': duree,
                'valeur_actuelle': round(valeur_actuelle, 2),
                'interets_totaux': round(interets_totaux, 2),
                'tableau': tableau,
                'label_periode': label_periode,
                'methode': 'simple'
            }

            contexte = {
                'montant': montant,
                'taux': taux * 100,
                'type_taux': type_taux,
                'duree': duree,
                'valeur_actuelle': round(valeur_actuelle, 2),
                'interets_totaux': round(interets_totaux, 2),
                'tableau': tableau,
                'label_periode': label_periode,
                'graphique': graphique,
                'resultat': True,
            }

        except (ValueError, TypeError, ZeroDivisionError):
            contexte['erreur'] = "Veuillez vérifier les valeurs saisies."

    return render(request, 'convertisseur/index.html', contexte)


# ==================== MÉTHODE AVANCÉE (Emprunts successifs) ====================

def methode_avancee(request):
    contexte = {}

    if request.method == 'POST':
        try:
            montant = float(request.POST.get('montant'))
            duree = int(request.POST.get('duree'))
            taux_final = float(request.POST.get('taux_final')) / 100

            # Récupération des taux par année
            taux_annuels = []
            for i in range(1, duree):
                taux_annuels.append(float(request.POST.get(f'taux_{i}')) / 100)

            # Calcul des flux annuels (intérêts reçus = montant * taux_final)
            interet_annuel = montant * taux_final

            # Calcul des emprunts successifs
            emprunts = []
            flux_emprunts = []
            solde = montant

            # Tableau des résultats
            tableau = []

            # Année 0 : placement initial
            tableau.append({
                'annee': 0,
                'placement': -montant,
                'emprunts': '',
                'solde': -montant
            })

            # Calcul des emprunts (de la dernière année vers la première)
            besoin = interet_annuel
            for i in range(duree - 1, 0, -1):
                emprunt = besoin / (1 + taux_annuels[i - 1])
                emprunts.insert(0, {
                    'annee': i,
                    'montant': round(emprunt, 2),
                    'taux': taux_annuels[i - 1] * 100,
                    'interet': round(emprunt * taux_annuels[i - 1], 2)
                })
                besoin = interet_annuel + (emprunt * taux_annuels[i - 1])

            # Construction du tableau des flux
            solde_initial = -montant
            flux_emprunts = [0] * (duree + 1)

            for emp in emprunts:
                annee = emp['annee']
                flux_emprunts[annee] -= emp['montant']
                for i in range(1, annee + 1):
                    if i < annee:
                        flux_emprunts[i] -= emp['interet']
                    else:
                        flux_emprunts[annee] += interet_annuel - emp['montant']

            # Génération du tableau final
            for annee in range(duree + 1):
                placement = interet_annuel if 0 < annee < duree else (
                    montant + interet_annuel if annee == duree else -montant)
                if annee == duree:
                    placement = montant + interet_annuel

                solde_cumule = placement + flux_emprunts[annee]

                tableau.append({
                    'annee': annee,
                    'placement': round(placement, 2) if annee > 0 else placement,
                    'flux_emprunts': round(flux_emprunts[annee], 2),
                    'solde': round(solde_cumule, 2) if annee == 0 else '',
                    'solde_final': round(solde_cumule, 2) if annee == duree else ''
                })

            # Graphique des intérêts
            plt.figure(figsize=(10, 5))
            annees = list(range(1, duree + 1))
            interets = [interet_annuel] * duree
            plt.bar(annees, interets, color='#4a9eff', alpha=0.7, label='Intérêts annuels')
            plt.plot(annees, interets, marker='o', color='#1a2a3a', linewidth=2)
            plt.title('Intérêts annuels')
            plt.xlabel('Année')
            plt.ylabel('Intérêts (€)')
            plt.grid(True, alpha=0.3)

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            graphique_interets = base64.b64encode(buffer.read()).decode()
            plt.close()

            # Graphique des taux
            plt.figure(figsize=(10, 5))
            taux_affiches = [t * 100 for t in taux_annuels]
            plt.plot(range(1, duree), taux_affiches, marker='s', color='#28a745', linewidth=2, markersize=8)
            plt.title('Structure des taux par année')
            plt.xlabel('Année')
            plt.ylabel('Taux (%)')
            plt.grid(True, alpha=0.3)

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            graphique_taux = base64.b64encode(buffer.read()).decode()
            plt.close()

            # Calcul du rendement net
            valeur_finale = tableau[-1]['solde_final']
            rendement = (valeur_finale / montant - 1) * 100

            # Sauvegarde en session
            request.session['resultats'] = {
                'montant': montant,
                'duree': duree,
                'taux_final': taux_final * 100,
                'taux_annuels': [t * 100 for t in taux_annuels],
                'tableau': tableau,
                'emprunts': emprunts,
                'rendement': round(rendement, 2),
                'methode': 'avancee'
            }

            contexte = {
                'montant': montant,
                'duree': duree,
                'taux_final': taux_final * 100,
                'taux_annuels': [t * 100 for t in taux_annuels],
                'tableau': tableau,
                'emprunts': emprunts,
                'graphique_interets': graphique_interets,
                'graphique_taux': graphique_taux,
                'rendement': round(rendement, 2),
                'resultat': True,
            }

        except Exception as e:
            contexte['erreur'] = f"Erreur: {str(e)}"

    return render(request, 'convertisseur/methode_avancee.html', contexte)


# ==================== EXPORT PDF ====================

def export_pdf(request):
    resultats = request.session.get('resultats', {})
    if not resultats:
        return HttpResponse("Aucun résultat à exporter", status=400)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Rapport de Conversion d'Obligations")

    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Montant: {resultats['montant']} €")
    p.drawString(50, height - 100,
                 f"Méthode: {'Simple (Zéro Coupon)' if resultats.get('methode') == 'simple' else 'Avancée (Emprunts successifs)'}")

    if resultats.get('methode') == 'simple':
        p.drawString(50, height - 120, f"Taux: {resultats['taux']}%")
        p.drawString(50, height - 140, f"Durée: {resultats['duree']} {resultats.get('label_periode', 'années')}")
        p.drawString(50, height - 160, f"Valeur actuelle: {resultats['valeur_actuelle']} €")
        p.drawString(50, height - 180, f"Intérêts totaux: {resultats['interets_totaux']} €")
    else:
        p.drawString(50, height - 120, f"Taux final: {resultats['taux_final']}%")
        p.drawString(50, height - 140, f"Durée: {resultats['duree']} ans")
        p.drawString(50, height - 160, f"Rendement net: {resultats['rendement']}%")

    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_obligations.pdf"'
    return response