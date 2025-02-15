from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
from io import BytesIO
from forms import ProspectionForm, LoginForm, DownloadExcelForm, NovaPharmaSalesForm, GilbertSalesForm, EricFavreSalesForm, TroisCheneSalesForm
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func
import logging
from models import Planning
from forms import PlanningForm
from models import db, User, Prospection, NovaPharmaProduct, GilbertProduct, EricFavreProduct, TroisCheneProduct, NovaPharmaSale, GilbertSale, EricFavreSale, TroisCheneSale

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plateforme_commerciale.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

csrf = CSRFProtect(app)
cache = Cache(app)

# Initialiser SQLAlchemy avec l'application Flask
db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d’utilisateur ou mot de passe incorrect', 'error')
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role != 'commercial':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    form = ProspectionForm()
    if form.validate_on_submit():
        try:
            prospection = Prospection(
                commercial_id=current_user.id,
                date=form.date.data,
                nom_client=form.nom_client.data,
                specialite=form.specialite.data,
                structure=form.structure.data,
                telephone=form.telephone.data,
                profils_prospect=form.profils_prospect.data,
                produits_presentés=form.produits_presentés.data,
                produits_prescrits=form.produits_prescrits.data
            )
            db.session.add(prospection)
            db.session.commit()
            flash('Données enregistrées avec succès', 'success')
            logger.info(f"Données enregistrées pour le commercial {current_user.username}")
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'enregistrement des données : {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    return render_template('dashboard.html', form=form)
    
@app.route('/visualiser_planning')
@login_required
def visualiser_planning():
    if current_user.role != 'commercial':
        return redirect(url_for('accueil'))

    # Récupérer les plannings du commercial connecté
    plannings = Planning.query.filter_by(commercial_id=current_user.id).all()
    return render_template('visualiser_planning.html', plannings=plannings)

@app.route('/saisie_planning', methods=['GET', 'POST'])
@login_required
def saisie_planning():
    if current_user.role != 'commercial':
        return redirect(url_for('accueil'))

    formulaire = PlanningForm()
    if formulaire.validate_on_submit():
        nouveau_planning = Planning(
            commercial_id=current_user.id,
            date=formulaire.date.data,
            lundi_matin=", ".join(request.form.getlist('lundi_matin')),
            lundi_soir=", ".join(request.form.getlist('lundi_soir')),
            mardi_matin=", ".join(request.form.getlist('mardi_matin')),
            mardi_soir=", ".join(request.form.getlist('mardi_soir')),
            mercredi_matin=", ".join(request.form.getlist('mercredi_matin')),
            mercredi_soir=", ".join(request.form.getlist('mercredi_soir')),
            jeudi_matin=", ".join(request.form.getlist('jeudi_matin')),
            jeudi_soir=", ".join(request.form.getlist('jeudi_soir')),
            vendredi_matin=", ".join(request.form.getlist('vendredi_matin')),
            vendredi_soir=", ".join(request.form.getlist('vendredi_soir')),
            samedi_matin=", ".join(request.form.getlist('samedi_matin')),
            samedi_soir=", ".join(request.form.getlist('samedi_soir')),
            dimanche_matin=", ".join(request.form.getlist('dimanche_matin')),
            dimanche_soir=", ".join(request.form.getlist('dimanche_soir')),
        )
        db.session.add(nouveau_planning)
        db.session.commit()
        return redirect(url_for('visualiser_planning'))

    return render_template('saisie_planning.html', formulaire=formulaire)

@app.route('/nasmedic_dashboard')
@login_required
def nasmedic_dashboard():
    # Récupérer les prospections pour NASMEDIC
    prospections = Prospection.query.join(User).filter(User.project == 'nasmedic').all()
    
    # Afficher les données dans la console pour débogage
    print("Prospections pour NASMEDIC:", prospections)
    
    # Vérifier si des données sont retournées
    if not prospections:
        flash("Aucune donnée trouvée pour NASMEDIC.", "info")
    
    # Récupérer le chiffre d'affaire mensuel pour NASMEDIC
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('revenue')
    ).filter(EricFavreSale.project == 'nasmedic').group_by('month').all()

    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_data = [row.revenue for row in monthly_revenue]

    # Afficher les données dans la console pour débogage
    print("Chiffre d'affaire mensuel:", monthly_revenue)
    print("Labels:", monthly_revenue_labels)
    print("Data:", monthly_revenue_data)
    
    # Récupérer les prospections pour NASMEDIC
    prospections = Prospection.query.join(User).filter(User.project == 'nasmedic').all()

    # Récupérer le classement des commerciaux (Top 5)
    top_5_commerciaux = db.session.query(
        User.username,
        User.zone,
        func.count(Prospection.id).label('nombre_visites')
    ).join(Prospection).filter(User.project == 'nasmedic').group_by(User.id).order_by(func.count(Prospection.id).desc()).limit(5).all()

    # Afficher les données dans la console pour débogage
    print("Top 5 commerciaux:", top_5_commerciaux)
    
    # Récupérer la liste des commerciaux pour NASMEDIC
    commerciaux = User.query.filter_by(project='nasmedic', role='commercial').all()

    # Afficher les données dans la console pour débogage
    print("Liste des commerciaux NASMEDIC:", commerciaux)

    return render_template('nasmedic_dashboard.html', monthly_revenue_labels=monthly_revenue_labels, monthly_revenue_data=monthly_revenue_data, top_5_commerciaux=top_5_commerciaux, commerciaux=commerciaux, prospections=prospections)
    
@app.route('/nasderm_dashboard')
@login_required
def nasderm_dashboard():
    # Récupérer les prospections pour NASDERM
    prospections = Prospection.query.join(User).filter(User.project == 'nasderm').all()
    
    # Afficher les données dans la console pour débogage
    print("Prospections pour NASDERM:", prospections)
    
    # Vérifier si des données sont retournées
    if not prospections:
        flash("Aucune donnée trouvée pour NASDERM.", "info")
    
    # Récupérer le chiffre d'affaire mensuel pour NASDERM
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('revenue')
    ).filter(NovaPharmaSale.project == 'nasderm').group_by('month').all()

    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_data = [row.revenue for row in monthly_revenue]

    # Afficher les données dans la console pour débogage
    print("Chiffre d'affaire mensuel NASDERM:", monthly_revenue)
    print("Labels:", monthly_revenue_labels)
    print("Data:", monthly_revenue_data)
    
    # Récupérer les prospections pour NASDERM
    prospections = Prospection.query.join(User).filter(User.project == 'nasderm').all()

    # Récupérer le classement des commerciaux (Top 5)
    top_5_commerciaux = db.session.query(
        User.username,
        User.zone,
        func.count(Prospection.id).label('nombre_visites')
    ).join(Prospection).filter(User.project == 'nasderm').group_by(User.id).order_by(func.count(Prospection.id).desc()).limit(5).all()

    # Afficher les données dans la console pour débogage
    print("Top 5 commerciaux:", top_5_commerciaux)
    
    # Récupérer la liste des commerciaux pour NASDERM
    commerciaux = User.query.filter_by(project='nasderm', role='commercial').all()

    # Afficher les données dans la console pour débogage
    print("Liste des commerciaux NASDERM:", commerciaux)

    return render_template('nasderm_dashboard.html', monthly_revenue_labels=monthly_revenue_labels, monthly_revenue_data=monthly_revenue_data, top_5_commerciaux=top_5_commerciaux, commerciaux=commerciaux, prospections=prospections)
   
    
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Calcul du chiffre d'affaire mensuel pour Nova Pharma
    nova_pharma_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('revenue')
    ).group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour Gilbert
    gilbert_revenue = db.session.query(
        func.strftime('%Y-%m', GilbertSale.date).label('month'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('revenue')
    ).group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour Eric Favre
    eric_favre_revenue = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('revenue')
    ).group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour 3 Chênes Pharma
    trois_chene_revenue = db.session.query(
        func.strftime('%Y-%m', TroisCheneSale.date).label('month'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('revenue')
    ).group_by('month').all()
    
    # Combiner les résultats dans un dictionnaire
    revenue_dict = {}
    for month, revenue in nova_pharma_revenue:
        revenue_dict[month] = {'nova_pharma_revenue': revenue or 0, 'gilbert_revenue': 0, 'eric_favre_revenue': 0, 'trois_chene_revenue': 0}
    
    for month, revenue in gilbert_revenue:
        if month in revenue_dict:
            revenue_dict[month]['gilbert_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': revenue or 0, 'eric_favre_revenue': 0, 'trois_chene_revenue': 0}
    
    for month, revenue in eric_favre_revenue:
        if month in revenue_dict:
            revenue_dict[month]['eric_favre_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': 0, 'eric_favre_revenue': revenue or 0, 'trois_chene_revenue': 0}
    
    for month, revenue in trois_chene_revenue:
        if month in revenue_dict:
            revenue_dict[month]['trois_chene_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': 0, 'eric_favre_revenue': 0, 'trois_chene_revenue': revenue or 0}
    
    # Convertir le dictionnaire en une liste pour le template
    monthly_revenue = []
    for month, revenues in revenue_dict.items():
        total = revenues['nova_pharma_revenue'] + revenues['gilbert_revenue'] + revenues['eric_favre_revenue'] + revenues['trois_chene_revenue']
        monthly_revenue.append((month, revenues['nova_pharma_revenue'], revenues['gilbert_revenue'], revenues['eric_favre_revenue'], revenues['trois_chene_revenue'], total))
    
    # Extraire les labels et les données pour le graphique
    monthly_revenue_labels = [row[0] for row in monthly_revenue]
    monthly_revenue_data = [row[5] for row in monthly_revenue]

    commerciaux = User.query.filter_by(role='commercial').all()
    top_5_commerciaux = db.session.query(User.username, User.zone, func.count(Prospection.id).label('nombre_visites')).join(Prospection).group_by(User.id).order_by(func.count(Prospection.id).desc()).limit(5).all()
    
    # Filtres pour le tableau récapitulatif
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    commercial_id = request.args.get('commercial')
    zone = request.args.get('zone')
    specialite = request.args.get('specialite')
    query = Prospection.query.join(User).filter(User.role == 'commercial')
    if date_start:
        query = query.filter(Prospection.date >= date_start)
    if date_end:
        query = query.filter(Prospection.date <= date_end)
    if commercial_id:
        query = query.filter(Prospection.commercial_id == commercial_id)
    if zone:
        query = query.filter(User.zone == zone)
    if specialite:
        query = query.filter(Prospection.specialite == specialite)
    prospections = query.all()
    
    return render_template('admin_dashboard.html', commerciaux=commerciaux, prospections=prospections, top_5_commerciaux=top_5_commerciaux, monthly_revenue_labels=monthly_revenue_labels, monthly_revenue_data=monthly_revenue_data)

# app.py
@app.route('/admin_plannings')
@login_required
def admin_plannings():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer tous les commerciaux
    commerciaux = User.query.filter_by(role='commercial').all()
    return render_template('admin_plannings.html', commerciaux=commerciaux)

@app.route('/admin_planning_detail/<int:commercial_id>')
@login_required
def admin_planning_detail(commercial_id):
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    # Récupérer les plannings du commercial sélectionné
    plannings = Planning.query.filter_by(commercial_id=commercial_id).all()
    commercial = User.query.get(commercial_id)

    return render_template('admin_planning_detail.html', plannings=plannings, commercial=commercial)

@app.route('/commercial_dashboard/<username>', methods=['GET', 'POST'])
@login_required
def commercial_dashboard(username):
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    commercial = User.query.filter_by(username=username).first()
    if not commercial:
        flash('Commercial non trouvé.', 'error')
        return redirect(url_for('admin_dashboard'))
    prospections = commercial.prospections

    # Utilisez ProspectionForm au lieu de DownloadExcelForm
    form = ProspectionForm()

    # Gérer le téléchargement Excel
    if request.method == 'POST' and 'download_excel' in request.form:
        try:
            # Préparer les données pour le fichier Excel
            data = [{
                'Date': p.date.strftime('%Y-%m-%d'),
                'Nom Client': p.nom_client,
                'Spécialité': p.specialite,
                'Structure': p.structure,
                'Téléphone': p.telephone,
                'Profils Prospect': p.profils_prospect,
                'Produits Présentés': p.produits_presentés,
                'Produits Prescrits': p.produits_prescrits
            } for p in prospections]
            df = pd.DataFrame(data)

            # Créer un fichier Excel en mémoire
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Prospections')
            output.seek(0)

            # Renvoyer le fichier Excel en téléchargement
            return send_file(output, download_name=f'prospections_{username}.xlsx', as_attachment=True)
        except Exception as e:
            flash(f'Erreur lors de la génération du fichier Excel : {str(e)}', 'error')
            logger.error(f"Erreur lors de la génération du fichier Excel : {str(e)}")

    return render_template('commercial_dashboard.html', commercial=commercial, prospections=prospections, form=form)

@app.route('/export_pdf/<username>')
@login_required
def export_pdf(username):
    commercial = User.query.filter_by(username=username).first()
    prospections = commercial.prospections
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Prospections de {username}")
    y = 700
    for prospection in prospections:
        p.drawString(100, y, f"Date: {prospection.date}, Client: {prospection.nom_client}")
        y -= 20
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name=f'prospections_{username}.pdf', as_attachment=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie', 'success')
    return redirect(url_for('home'))

@app.route('/nova_pharma_sales', methods=['GET', 'POST'])
@login_required
def nova_pharma_sales():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les produits de Nova Pharma
    products = NovaPharmaProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('nova_pharma_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}')
            
            if quantity and int(quantity) > 0:
                sale = NovaPharmaSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'  # Ajoutez ce champ
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Nova Pharma enregistrées avec succès', 'success')
        return redirect(url_for('nova_pharma_sales'))
    
    return render_template('nova_pharma_sales.html', products=products)

@app.route('/gilbert_sales', methods=['GET', 'POST'])
@login_required
def gilbert_sales():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les produits de Gilbert
    products = GilbertProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('gilbert_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}')
            
            if quantity and int(quantity) > 0:
                sale = GilbertSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'  # Ajoutez ce champ
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Gilbert enregistrées avec succès', 'success')
        return redirect(url_for('gilbert_sales'))
    
    return render_template('gilbert_sales.html', products=products)

@app.route('/eric_favre_sales', methods=['GET', 'POST'])
@login_required
def eric_favre_sales():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les produits d'Eric Favre
    products = EricFavreProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('eric_favre_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}')
            
            if quantity and int(quantity) > 0:
                sale = EricFavreSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasmedic'  # Ajoutez ce champ
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Eric Favre enregistrées avec succès', 'success')
        return redirect(url_for('eric_favre_sales'))
    
    return render_template('eric_favre_sales.html', products=products)

@app.route('/trois_chene_sales', methods=['GET', 'POST'])
@login_required
def trois_chene_sales():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les produits de 3 Chênes Pharma
    products = TroisCheneProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('trois_chene_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}')
            
            if quantity and int(quantity) > 0:
                sale = TroisCheneSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasmedic'  # Ajoutez ce champ
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes 3 Chênes Pharma enregistrées avec succès', 'success')
        return redirect(url_for('trois_chene_sales'))
    
    return render_template('trois_chene_sales.html', products=products)

@app.route('/monthly_revenue')
@login_required
def monthly_revenue():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Calcul du chiffre d'affaire mensuel pour Nova Pharma
    nova_pharma_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('revenue')
    ).filter(NovaPharmaSale.project == 'nasderm').group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour Gilbert
    gilbert_revenue = db.session.query(
        func.strftime('%Y-%m', GilbertSale.date).label('month'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('revenue')
    ).filter(GilbertSale.project == 'nasderm').group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour 3 Chênes Pharma
    trois_chene_revenue = db.session.query(
        func.strftime('%Y-%m', TroisCheneSale.date).label('month'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('revenue')
    ).filter(TroisCheneSale.project == 'nasmedic').group_by('month').all()
    
    # Combiner les résultats dans un dictionnaire
    revenue_dict = {}
    for month, revenue in nova_pharma_revenue:
        revenue_dict[month] = {'nova_pharma_revenue': revenue or 0, 'gilbert_revenue': 0, 'trois_chene_revenue': 0}
    
    for month, revenue in gilbert_revenue:
        if month in revenue_dict:
            revenue_dict[month]['gilbert_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': revenue or 0, 'trois_chene_revenue': 0}
    
    for month, revenue in trois_chene_revenue:
        if month in revenue_dict:
            revenue_dict[month]['trois_chene_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': 0, 'trois_chene_revenue': revenue or 0}
    
    # Convertir le dictionnaire en une liste pour le template
    monthly_revenue = []
    for month, revenues in revenue_dict.items():
        total = revenues['nova_pharma_revenue'] + revenues['gilbert_revenue'] + revenues['trois_chene_revenue']
        monthly_revenue.append((month, revenues['nova_pharma_revenue'], revenues['gilbert_revenue'], revenues['trois_chene_revenue'], total))
    
    return render_template('monthly_revenue.html', monthly_revenue=monthly_revenue)

@app.route('/monthly_revenue_nasmedic')
@login_required
def monthly_revenue_nasmedic():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Calcul du chiffre d'affaire mensuel pour Eric Favre
    eric_favre_revenue = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('revenue')
    ).filter(EricFavreSale.project == 'nasmedic').group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour 3 Chênes Pharma
    trois_chene_revenue = db.session.query(
        func.strftime('%Y-%m', TroisCheneSale.date).label('month'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('revenue')
    ).filter(TroisCheneSale.project == 'nasmedic').group_by('month').all()
    
    # Combiner les résultats dans un dictionnaire
    revenue_dict = {}
    for month, revenue in eric_favre_revenue:
        revenue_dict[month] = {'eric_favre_revenue': revenue or 0, 'trois_chene_revenue': 0}
    
    for month, revenue in trois_chene_revenue:
        if month in revenue_dict:
            revenue_dict[month]['trois_chene_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'eric_favre_revenue': 0, 'trois_chene_revenue': revenue or 0}
    
    # Convertir le dictionnaire en une liste pour le template
    monthly_revenue = []
    for month, revenues in revenue_dict.items():
        total = revenues['eric_favre_revenue'] + revenues['trois_chene_revenue']
        monthly_revenue.append((month, revenues['eric_favre_revenue'], revenues['trois_chene_revenue'], total))
    
    return render_template('monthly_revenue_nasmedic.html', monthly_revenue=monthly_revenue)

@app.route('/monthly_revenue_nasderm')
@login_required
def monthly_revenue_nasderm():
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Calcul du chiffre d'affaire mensuel pour Nova Pharma
    nova_pharma_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('revenue')
    ).filter(NovaPharmaSale.project == 'nasderm').group_by('month').all()
    
    # Calcul du chiffre d'affaire mensuel pour Gilbert
    gilbert_revenue = db.session.query(
        func.strftime('%Y-%m', GilbertSale.date).label('month'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('revenue')
    ).filter(GilbertSale.project == 'nasderm').group_by('month').all()
    
    # Combiner les résultats dans un dictionnaire
    revenue_dict = {}
    for month, revenue in nova_pharma_revenue:
        revenue_dict[month] = {'nova_pharma_revenue': revenue or 0, 'gilbert_revenue': 0}
    
    for month, revenue in gilbert_revenue:
        if month in revenue_dict:
            revenue_dict[month]['gilbert_revenue'] = revenue or 0
        else:
            revenue_dict[month] = {'nova_pharma_revenue': 0, 'gilbert_revenue': revenue or 0}
    
    # Convertir le dictionnaire en une liste pour le template
    monthly_revenue = []
    for month, revenues in revenue_dict.items():
        total = revenues['nova_pharma_revenue'] + revenues['gilbert_revenue']
        monthly_revenue.append((month, revenues['nova_pharma_revenue'], revenues['gilbert_revenue'], total))
    
    return render_template('monthly_revenue_nasderm.html', monthly_revenue=monthly_revenue)

@app.route('/monthly_revenue_detail_nasmedic/<month>')
@login_required
def monthly_revenue_detail_nasmedic(month):
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Détail des ventes pour Eric Favre
    eric_favre_sales = db.session.query(
        EricFavreProduct.name,
        func.sum(EricFavreSale.quantity).label('total_quantity'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('total_revenue')
    ).join(EricFavreSale).filter(func.strftime('%Y-%m', EricFavreSale.date) == month).group_by(EricFavreProduct.name).all()
    
    # Détail des ventes pour 3 Chênes Pharma
    trois_chene_sales = db.session.query(
        TroisCheneProduct.name,
        func.sum(TroisCheneSale.quantity).label('total_quantity'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('total_revenue')
    ).join(TroisCheneSale).filter(func.strftime('%Y-%m', TroisCheneSale.date) == month).group_by(TroisCheneProduct.name).all()
    
    return render_template('monthly_revenue_detail_nasmedic.html', month=month, eric_favre_sales=eric_favre_sales, trois_chene_sales=trois_chene_sales)
    
@app.route('/monthly_revenue_detail_nasderm/<month>')
@login_required
def monthly_revenue_detail_nasderm(month):
    if current_user.role not in ['admin', 'commercial']:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Détail des ventes pour Nova Pharma
    nova_pharma_sales = db.session.query(
        NovaPharmaProduct.name,
        func.sum(NovaPharmaSale.quantity).label('total_quantity'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('total_revenue')
    ).join(NovaPharmaSale).filter(func.strftime('%Y-%m', NovaPharmaSale.date) == month).group_by(NovaPharmaProduct.name).all()
    
    # Détail des ventes pour Gilbert
    gilbert_sales = db.session.query(
        GilbertProduct.name,
        func.sum(GilbertSale.quantity).label('total_quantity'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('total_revenue')
    ).join(GilbertSale).filter(func.strftime('%Y-%m', GilbertSale.date) == month).group_by(GilbertProduct.name).all()
    
    return render_template('monthly_revenue_detail_nasderm.html', month=month, nova_pharma_sales=nova_pharma_sales, gilbert_sales=gilbert_sales)    

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

def create_initial_users():
    with app.app_context():
        if not User.query.filter_by(username="Anna Diallo").first():
            db.session.add(User(username="Anna Diallo", password=generate_password_hash("admin123", method="pbkdf2:sha256"), role="admin", zone=None, project='nasmedic'))
        commerciaux_nasmedic = [
            ("KHALIFA DIOP", "khalifa123", "CENTRE VILLE", 'nasmedic'),
            ("AMADOU DEME", "amadou123", "Banlieue 1", 'nasmedic'),
            ("MBAYE NDOYE", "mbaye123", "THIES", 'nasmedic'),
            ("MEDINA K NDIAYE", "medina123", "ZONES INTERMEDIAIRE 2", 'nasmedic'),
            ("MARIE LOUISE", "marie123", "MBOUR", 'nasmedic'),
            ("FATOU COLLETTE DRAME", "fatou123", "ZONES INTERMEDIAIRE 1", 'nasmedic'),
            ("MASSAMBA MBAYE", "massamba123", "Banlieue 2", 'nasmedic'),
            ("LAMINE THIOUB", "lamine123", "REGION DE DIOURBEL", 'nasmedic'),
        ]
        for username, password, zone, project in commerciaux_nasmedic:
            if not User.query.filter_by(username=username).first():
                db.session.add(User(username=username, password=generate_password_hash(password, method="pbkdf2:sha256"), role="commercial", zone=zone, project=project))
        
        commerciaux_nasderm = [
            ("FAMA DIOP", "fama123", "CENTRE VILLE", 'nasderm'),
            ("MARIE JEANNE DIOUF", "marie123", "Banlieue 1", 'nasderm'),
            ("ASTOU MANA MBENGUE", "astou123", "THIES", 'nasderm'),
            ("HONORINE", "honorine123", "ZONES INTERMEDIAIRE 2", 'nasderm'),
            ("MIJO", "mijo123", "MBOUR", 'nasderm'),
            ("HELENE FAYE", "helene123", "ZONES INTERMEDIAIRE 1", 'nasderm'),
            ("ADJARA CISSÉ", "adjara123", "Banlieue 2", 'nasderm'),
            ("KHAR FALL", "khar123", "REGION DE DIOURBEL", 'nasderm'),
            ("KHADY SOW", "khady123", "REGION DE DIOURBEL", 'nasderm'),
        ]
        for username, password, zone, project in commerciaux_nasderm:
            if not User.query.filter_by(username=username).first():
                db.session.add(User(username=username, password=generate_password_hash(password, method="pbkdf2:sha256"), role="commercial", zone=zone, project=project))
        
        db.session.commit()

def create_initial_products():
    with app.app_context():
        # Produits Nova Pharma
        nova_pharma_products = [
            ("HYFAC GEL NETTOYANT FLC 150ML", 3.5),
            ("HYFAC GEL NETTOYANT TB 300ML", 3.5),
            ("HYFAC PAIN NETTOYANT 100G SOUS ETUI", 3.5),
            ("HYFAC MOUSSE NETTOYANTE FLC150ML", 3.5),
            ("HYFAC SOIN GLOBAL FLC40ML/ETUI", 3.5),
            ("HYFAC ETUI 2X15 PATCHS IMPERFECTIONS", 3.5),
            ("HYFAC MOUSSE A RASER SENSITIVE FLC150ML", 3.5),
            ("HYFAC SUN SPF 50+ INV TB 40ML SS ETUI", 3.5),
            ("CLARIFAC Soin anti-taches 40ML", 3.5),
            ("HYFAC WOMAN SOIN GLOBAL TB 40ML/ETUI", 3.5),
            ("HYFAC WOMAN LOTION VISAGE FL 200 ML", 3.5),
            ("HYFAC WOMAN ACTIVE MASK 15*5ML", 3.5),
            ("HYDRAFAC CREME HYDRA LEGERE TUBE40 ML", 3.5),
        ]
        for name, price in nova_pharma_products:
            if not NovaPharmaProduct.query.filter_by(name=name).first():
                db.session.add(NovaPharmaProduct(name=name, default_price=price))

        # Produits Gilbert
        gilbert_products = [
            ("ELLE TEST BTE DE 1 TEST GROSSESSE", 3.5),
            ("MOUSTIDOSE SPRAY REPULSIF ZONE INFESTEES IR3535 +12M  100ML", 3.5),
            ("MOUSTIDOSE SPRAY REPULSIF ACTIF VÉGÉTAL +6M 100ML", 3.5),
            ("MOUSTIDOSE SPRAY REPULSIF ZONE TRES INFESTEES ICARIDINE  +24M 100ML", 3.5),
            ("MOUSTIDOSE CREME SOIN CALMANT  40ML", 3.5),
            ("WATERWIPES LINGETTES BD BB 4X60", 3.5),
            ("WATERWIPES LINGETTES BD BB X60", 3.5),
            ("WATERWIPES LINGETTES BD BB X28", 3.5),
            ("LEL SUCE NOUVEAU NE SYM ROSE PANACH 2X3", 3.5),
            ("LEL SUCE NOUVEAU NE SYM BLEU PANACHE 2X3", 3.5),
            ("LEL SUCE NOUVEAU NE SYM JAUNE", 3.5),
            ("LEL DUO SUCE ANA 0-6M LAPIN + CŒUR", 3.5),
            ("LEL DUO SUCE ANA 0-6M RENARD + CŒUR", 3.5),
            ("LEL SUCE 0-6M ANA MAMAN ANNEAU", 3.5),
            ("LEL SUCE 0-6M ANA PAPA ANNEAU", 3.5),
            ("LEL SUCE NUIT 0-6M ANA ELEPH BLEU ANNEAU", 3.5),
            ("LEL SUCE NUIT  0-6M ANA ELEPH ROSE ANNEAU", 3.5),
            ("SUCETTE 0-6 MOIS PHYSIOLOGIQUE (BÉBÉ ALLAITÉ) ELEPHANT", 3.5),
            ("LEL SUCE 0-6M PHYS BB AMOUR ANNEAU", 3.5),
            ("LEL SUCE 6-18M ANA BEBE AMOUR ANNEAU", 3.5),
            ("LEL SUCE 6-18M ANA MAMAN ANNEAU", 3.5),
            ("LEL SUCE 6-18M ANA PAPA ANNEAU", 3.5),
            ("LEL SUCE 6-18M PHYS DIS MOI  ANNEAU", 3.5),
            ("LEL SUCE +18M ANA JAIME PARENTS ANNEAU", 3.5),
            ("LEL BIBERON PLASTIQUE 150ML SAVANE PP", 3.5),
            ("LEL BIBERON ERGOSENSE 270ML SAVANE PP", 3.5),
            ("LEL BIBERON PLASTIQUE 330ML SAVANE PP", 3.5),
            ("LEL BIBERON VERRE 120ML", 3.5),
            ("LEL BIBERON VERRE 240ML", 3.5),
            ("LEL TETINE ERGOSENSE SIL. DEB. LENT (X2)", 3.5),
            ("LEL TETINE ERGOSENSE SIL. DEB. MOY (X2)", 3.5),
            ("LEL TETINE ERGOSENSE SIL.DEB.VAR (X2)", 3.5),
            ("LEL TETINE ERGOSENSE DEB. LIQ.EPAIS (X2)", 3.5),
            ("LEL ATTACHE SUCETTE 2023", 3.5),
            ("LEL ANNEAU DENTITION FORME HOCHET", 3.5),
            ("LEL COUPE ONGLES BEBE", 3.5),
            ("LEL CISEAUX DROITS", 3.5),
            ("LEL 60 BATONNETS EMBOUT BEBE", 3.5),
            ("LEL GOUPILLON", 3.5),
            ("NEUTRADERM BAUME RELIPIDANT 400ML RELIPID +", 3.5),
            ("NEUTRADERM BAUME RELIPIDANT 200ML RELIPID +", 3.5),
            ("NEUTRADERM HUILE LAVANTE RELIPIDANTE 400ML RELIPID +", 3.5),
            ("NEUTRADERM HUILE LAVANTE RELIPIDANTE 1L RELIPID +", 3.5),
            ("NEUTRADERM CREME DE DOUCHE RELIPIDANTE 400ML RELIPID +", 3.5),
            ("NEUTRADERM CREME DE DOUCHE RELIPIDANTE 200ML RELIPID +", 3.5),
            ("NEUTRADERM GEL DOUCHE SURGRAS DERMO-PROTECTEUR TB 200ML", 3.5),
            ("NEUTRADERM GEL DOUCHE SURGRAS DERMO-PROTECTEUR 500ML", 3.5),
            ("NEUTRADERM GEL DOUCHE SURGRAS DERMO-PROTECTEUR 1 LITRE", 3.5),
            ("NEUTRADERM SAVON SURGRAS DERMO-PROTECTEUR 200G", 3.5),
            ("NEUTRADERM GEL CREME NOURISSANT DERMO-PROTECTEUR TB 200ML", 3.5),
            ("NEUTRADERM GEL CREME NOURISSANT DERMO-PROTECTEUR 400ML", 3.5),
            ("NEUTRADERM GEL DOUCHE MICELLAIRE DERMO-APAISANT 1L", 3.5),
            ("NEUTRADERM GEL CREME HYDRATANT DERMO-APAISANT TB 200ML", 3.5),
            ("NEUTRADERM GEL CREME HYDRATANT DERMO-APAISANT 400ML", 3.5),
            ("NEUTRADERM BABY GEL NETTOYANT DOUCEUR 3 EN 1 TB 200ML", 3.5),
            ("NEUTRADERM BABY GEL NETTOYANT DOUCEUR 3 EN 1 FL. POMPE 400ML", 3.5),
            ("NEUTRADERM BABY EAU NETTOYANTE DOUCEUR 3 EN 1 FL. CAPS. 200ML", 3.5),
            ("NEUTRADERM BABY EAU NETTOYANTE DOUCEUR 3 EN 1 FL. POMPE 1L", 3.5),
            ("NEUTRADERM BABY CREME HYDRATANTE APAISANTE TB AVEC ETUI 100ML", 3.5),
            ("NEUTRADERM SOIN LAVANT DOUCEUR INTIME FL250ML", 3.5),
            ("NEUTRADERM SOIN LAVANT DOUCEUR INTIME FL500ML", 3.5),
            ("NEUTRADERM CRÈME APAISANTE DOUCEUR INTIME 40ML", 3.5),
            ("NEUTRADERM BRUME D'EAU, SOIN APAISANT 150ML", 3.5),
            ("NEUTRADERM BRUME D'EAU, SOIN APAISANT 300ML", 3.5),
            ("LAINO GEL CREME  HYDRATANTE ANTI OXYDANT 40ML REPACK", 3.5),
            ("LAINO CREME NOURRISSANTE ANTI OXYDANT 40ML REPACK", 3.5),
            ("LAINO SERUM HYDRATANT ANTI OXYDANT 30ML REPACK", 3.5),
            ("LAINO CONTOUR DES YEUX HYDRATANT 15ML REPACK", 3.5),
            ("LAINO GEL NETTOYANT DEMAQUILLANT 200ML REPACK", 3.5),
            ("LAINO GOMMAGE HYDRATANT TB75ML", 3.5),
            ("LAINO MASQUE HYDRATANT TB75ML", 3.5),
            ("LAINO LAIT HYDRATANT AMANDE DOUCE FL400ML", 3.5),
            ("LAINO SOIN NUTRITIF INTENSE OLIVE FLC400ML", 3.5),
            ("LAINO LAIT NUTRI CONFORT KARITE FLC400ML", 3.5),
            ("LAINO LAIT NUTRI BIEN ETRE ROSE  FL400ML", 3.5),
            ("LAINO LAIT NUTRI FERMETE ARGAN FLC400ML", 3.5),
            ("LAINO SAVON SOUFRE  SOUS ETUI 150G", 3.5),
            ("LAINO SOIN LEVRE PRO INTENSE STICK 4G", 3.5),
            ("LAINO SOIN LEVRES FIGUE 4G huiles végétales", 3.5),
            ("LAI SOIN DES LEVRES FRAISE 4G", 3.5),
            ("LAI SOIN DES LEVRES VANILLE 4G", 3.5),
            ("LAI SOIN DES LEVRES GRENADINE 4G", 3.5),
            ("LAI SOIN DES LEVRES COCO 4G", 3.5),
            ("LAI SOIN DES LEVRES FRAMBOISE 4G", 3.5),
            ("LAI SOIN DES LEVRES CERISE 4G", 3.5),
            ("LAI SOIN DES LEVRES POMME 4G", 3.5),
            ("LAI SOIN DES LEVRES CASSIS 4G", 3.5),
            ("LAINO CREME MAIN PRO INTENSE TB50ML", 3.5),
            ("LAINO SAVON SOLIDE D'ALEP ETUI150GR", 3.5),
            ("LAINO SAVON LIQ MARSEILLE FLC300ML", 3.5),
            ("LAINO L'AUTHENTIQUE SAVON MARSEILLE 150G", 3.5),
            ("LAINO PATE ARGILE VERTE TB350G", 3.5),
            ("LAINO ARGILE POUDRE SURFINE ETUI300G", 3.5),
            ("LAINO EAU DE ROSE FLC250ML", 3.5),
            ("LAINO EAU FLORALE DE BLEUET FLC250ML", 3.5),
            ("LAINO EAU DE FLEUR D'ORANGER FLC250ML", 3.5),
        ]
        for name, price in gilbert_products:
            if not GilbertProduct.query.filter_by(name=name).first():
                db.session.add(GilbertProduct(name=name, default_price=price))

        # Produits Eric Favre
        eric_favre_products = [
            ("Chronoerect", 3.58),
            ("Special Kid calcium", 2.65),
            ("Special Kid Fer", 2.65),
            ("Special kid immunite", 3.00),
            ("Special Kid multivit", 2.65),
            ("Special Kid nez et gorge", 2.65),
            ("Special kid nutri+", 2.65),
            ("Special kid probiotiques", 8.56),
            ("Special kid rehydratation", 2.65),
            ("Special kid sol spray nasal F/50ML", 2.65),
            ("Special Kid sommeil", 2.65),
            ("Special kid Soulage doux", 2.65),
            ("Special kid Zinc", 2.65),
            ("Time Sex Control", 6.90),
            ("Appetit Plus", 2.34),
        ]
        for name, price in eric_favre_products:
            if not EricFavreProduct.query.filter_by(name=name).first():
                db.session.add(EricFavreProduct(name=name, default_price=price))

        # Produits 3 Chênes Pharma
        trois_chene_products = [
            ("ASTHE 1000", 6.05),
            ("BOIS BANDE", 3.45),
            ("CARBOLINE CPR B/30", 2.40),
            ("DIARILIUM ENFANT SOL BUV", 1.95),
            ("DIARILIUM SOL BV UNICADOSE", 2.64),
            ("DYSMECALM CPR B/15", 2.90),
            ("EASY MOM GROSSESSE GEL B/30", 3.70),
            ("EFIRUB CPR B/30", 3.50),
            ("EFIRUB PDRE SOL BUV SACH B/8", 3.45),
            ("FLATUPLEXIN", 4.80),
            ("MYOCALM", 3.55),
            ("OSTEOPHYTUM CP", 7.50),
            ("OSTEOPHYTUM GEL 100ML", 4.75),
            ("OSTEOPHYTUM PATCH/14", 2.55),
            ("SEDABUCCIL", 3.60),
            ("SOMNIPLEX MELATONINE CPR", 5.20),
            ("VAGALINE SPRAY BUCCAL F/25ML", 3.75),
            ("VAGALINE CPR B/15", 2.45),
            ("SPRAY NASAL", 3.75),
            ("MYOCALM ROLL ON 50ML", 4.20),
            ("MYOCALM SPRAY 100ML", 4.25),
            ("INFLAKIN/30", 8.95),
            ("INFLAKIN/10", 5.15),
        ]
        for name, price in trois_chene_products:
            if not TroisCheneProduct.query.filter_by(name=name).first():
                db.session.add(TroisCheneProduct(name=name, default_price=price))

        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_initial_users()
        create_initial_products()
    app.run(debug=True)