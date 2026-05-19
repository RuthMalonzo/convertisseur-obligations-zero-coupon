# 📊 Convertisseur d'Obligations Zéro Coupon

Application web Django professionnelle pour convertir des obligations classiques en obligations Zéro Coupon.

## ✨ Fonctionnalités

- 🔄 Conversion d'obligations classiques → Zéro Coupon
- 📈 Support des taux **annuels** et **mensuels**
- 📊 Tableau d'amortissement détaillé période par période
- 📈 Graphiques dynamiques des intérêts (Matplotlib)
- 📄 Export des résultats en PDF (ReportLab)
- 💾 Historique des calculs en base de données
- 📧 Envoi des résultats par email
- 🏦 Interface inspirée des banques d'investissement

## 🛠️ Stack Technique

- **Backend** : Django, Python
- **Base de données** : SQLite
- **Graphiques** : Matplotlib
- **PDF** : ReportLab
- **Frontend** : HTML5, CSS3

## 🚀 Installation

```bash
git clone https://github.com/RuthMalonzo/convertisseur-obligations-zero-coupon.git
cd convertisseur-obligations-zero-coupon
pip install django matplotlib reportlab
python manage.py migrate
python manage.py runserver
