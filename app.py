# app.py
from flask import Flask
from extensions import db  # On importe db depuis extensions.py

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Exemple avec SQLite
db.init_app(app)  # On relie db à l'application Flask

# On importe les modèles APRÈS avoir créé app et db
from models import User, Prospection, NovaPharmaProduct, GilbertProduct, EricFavreProduct, TroisCheneProduct, NovaPharmaSale, GilbertSale, EricFavreSale, TroisCheneSale, Planning

# Le reste de ton code (routes, etc.)
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pandas as pd
from io import BytesIO
from forms import ProspectionForm, LoginForm, DownloadExcelForm, NovaPharmaSalesForm, GilbertSalesForm, EricFavreSalesForm, TroisCheneSalesForm, PlanningForm, UserForm, AdminEricFavreSaleForm, AdminGilbertSaleForm, AdminTroisCheneSaleForm, AddEricFavreProductForm, AddGilbertProductForm, AddTroisCheneProductForm, AdminSaleForm, AddNovaPharmaProductForm
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, and_
import logging
from sqlalchemy.orm import aliased
from sqlalchemy import or_
from models import db, User, Prospection, NovaPharmaProduct, GilbertProduct, EricFavreProduct, TroisCheneProduct, NovaPharmaSale, GilbertSale, EricFavreSale, TroisCheneSale, Planning

app = Flask(__name__)
app.secret_key = 'un_secret_key_tres_secret'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plateforme_commerciale.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['SECRET_KEY'] = 'une_clé_ultra_secrète_et_longue'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

csrf = CSRFProtect(app)
cache = Cache(app)

# Initialiser SQLAlchemy avec l'application Flask
db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager(app)
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
            flash("Nom d'utilisateur ou mot de passe incorrect", "error")
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])  
@login_required
def dashboard():
    try:
        form = ProspectionForm()
        prospections = Prospection.query.filter_by(commercial_id=current_user.id).order_by(Prospection.date.desc()).all()
        
        # Calcul des produits présentés
        produits_presentes_count = 0
        for p in prospections:
            if p.produits_presentes:
                produits_presentes_count += len(p.produits_presentes.split(','))
        
        # Calcul du taux de conversion
        if prospections:
            prospections_avec_prescriptions = [p for p in prospections if p.produits_prescrits]
            taux_conversion = round((len(prospections_avec_prescriptions) / len(prospections)) * 100)
        else:
            taux_conversion = 0
            
        return render_template('dashboard.html',
                            form=form,
                            prospections=prospections,
                            produits_presentes_count=produits_presentes_count,
                            taux_conversion=taux_conversion)
                            
    except Exception as e:
        app.logger.error(f"Error in dashboard: {str(e)}")
        return render_template('dashboard.html', 
                            form=ProspectionForm(),
                            prospections=[],
                            produits_presentes_count=0,
                            taux_conversion=0)

@app.route('/prospection', methods=['GET', 'POST'])
@login_required
def add_prospection():
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
                produits_presentes=form.produits_presentes.data,
                produits_prescrits=form.produits_prescrits.data
            )
            db.session.add(prospection)
            db.session.commit()
            flash('Prospection enregistrée avec succès', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", 'error')
    return render_template('add_prospection.html', form=form)

@app.route('/visualiser_planning')
@login_required
def visualiser_planning():
    plannings = Planning.query.filter_by(commercial_id=current_user.id).all()
    return render_template('visualiser_planning.html', plannings=plannings)

@app.route('/saisie_planning', methods=['GET', 'POST'])
@login_required
def saisie_planning():
    form = PlanningForm()
    if form.validate_on_submit():
        try:
            planning = Planning(
                commercial_id=current_user.id,
                date=form.date.data,
                lundi_matin=", ".join(form.lundi_matin.data),
                lundi_soir=", ".join(form.lundi_soir.data),
                mardi_matin=", ".join(form.mardi_matin.data),
                mardi_soir=", ".join(form.mardi_soir.data),
                mercredi_matin=", ".join(form.mercredi_matin.data),
                mercredi_soir=", ".join(form.mercredi_soir.data),
                jeudi_matin=", ".join(form.jeudi_matin.data),
                jeudi_soir=", ".join(form.jeudi_soir.data),
                vendredi_matin=", ".join(form.vendredi_matin.data),
                vendredi_soir=", ".join(form.vendredi_soir.data),
                samedi_matin=", ".join(form.samedi_matin.data),
                samedi_soir=", ".join(form.samedi_soir.data),
                dimanche_matin=", ".join(form.dimanche_matin.data),
                dimanche_soir=", ".join(form.dimanche_soir.data)
            )
            db.session.add(planning)
            db.session.commit()
            flash('Planning enregistré avec succès', 'success')
            return redirect(url_for('visualiser_planning'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", 'error')
    return render_template('saisie_planning.html', form=form)

@app.route('/mes_ventes')
@login_required
def mes_ventes():
    if current_user.project == 'nasmedic':
        ventes_eric = EricFavreSale.query.filter_by(commercial_id=current_user.id).all()
        ventes_trois = TroisCheneSale.query.filter_by(commercial_id=current_user.id).all()
        return render_template('mes_ventes.html', ventes_eric=ventes_eric, ventes_trois=ventes_trois)

    elif current_user.project == 'nasderm':
        ventes_nova = NovaPharmaSale.query.filter_by(commercial_id=current_user.id).all()
        ventes_gilbert = GilbertSale.query.filter_by(commercial_id=current_user.id).all()
        return render_template('mes_ventes.html', ventes_nova=ventes_nova, ventes_gilbert=ventes_gilbert)

    else:
        flash("Projet inconnu", "error")
        return redirect(url_for('dashboard'))


@app.route('/planning/<project>')
@login_required
def planning_par_projet(project):
    if current_user.role != 'admin':
        flash("Accès réservé à l'administrateur", "danger")
        return redirect(url_for('dashboard'))

    commerciaux = User.query.filter_by(project=project, role='commercial').all()
    return render_template('planning_liste_commerciaux.html', commerciaux=commerciaux, project=project)

@app.route('/planning/commercial/<int:commercial_id>')
@login_required
def planning_du_commercial(commercial_id):
    if current_user.role != 'admin':
        flash("Accès réservé à l'administrateur", "danger")
        return redirect(url_for('dashboard'))

    commercial = User.query.get_or_404(commercial_id)
    planning = Planning.query.filter_by(commercial_id=commercial_id).order_by(Planning.date.desc()).all()

    return render_template('planning_du_commercial.html', commercial=commercial, planning=planning)


@app.route('/nasmedic_dashboard')
@login_required
def nasmedic_dashboard():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les paramètres de filtre
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    commercial_id = request.args.get('commercial')
    
    # Construire la requête de base
    query = Prospection.query.join(User).filter(User.project == 'nasmedic')
    
    # Appliquer les filtres
    if date_start:
        query = query.filter(Prospection.date >= date_start)
    if date_end:
        query = query.filter(Prospection.date <= date_end)
    if commercial_id:
        query = query.filter(Prospection.commercial_id == commercial_id)
    
    prospections = query.all()
    
    # Calcul des KPI
    total_revenue = db.session.query(
        func.sum(EricFavreSale.quantity * EricFavreSale.price) + func.sum(TroisCheneSale.quantity * TroisCheneSale.price)
    ).filter(
        or_(
            EricFavreSale.project == 'nasmedic',
            TroisCheneSale.project == 'nasmedic'
        )
    ).scalar() or 0
    
    total_visits = len(prospections)
    
    # Récupérer le chiffre d'affaire mensuel pour NASMEDIC
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('eric_favre_revenue'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('trois_chene_revenue')
    ).outerjoin(TroisCheneSale, func.strftime('%Y-%m', TroisCheneSale.date) == func.strftime('%Y-%m', EricFavreSale.date)) \
     .filter(or_(EricFavreSale.project == 'nasmedic', TroisCheneSale.project == 'nasmedic')) \
     .group_by('month').order_by('month').all()
    
    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_eric = [row.eric_favre_revenue or 0 for row in monthly_revenue]
    monthly_revenue_trois = [row.trois_chene_revenue or 0 for row in monthly_revenue]
    monthly_revenue_total = [sum(x) for x in zip(monthly_revenue_eric, monthly_revenue_trois)]
    
    # Récupérer le classement des commerciaux (Top 5)
    top_5_commerciaux = db.session.query(
        User.username,
        User.zone,
        func.count(Prospection.id).label('nombre_visites')
    ).join(Prospection).filter(User.project == 'nasmedic').group_by(User.id).order_by(func.count(Prospection.id).desc()).limit(5).all()
    
    # Récupérer la liste des commerciaux pour NASMEDIC
    commerciaux = User.query.filter_by(project='nasmedic', role='commercial').all()

    return render_template(
        'nasmedic_dashboard.html',
        monthly_revenue_labels=monthly_revenue_labels,
        monthly_revenue_eric=monthly_revenue_eric,
        monthly_revenue_trois=monthly_revenue_trois,
        monthly_revenue_total=monthly_revenue_total,
        top_5_commerciaux=top_5_commerciaux,
        commerciaux=commerciaux,
        prospections=prospections,
        total_revenue=total_revenue,
        total_visits=total_visits,
        date_start=date_start,
        date_end=date_end,
        commercial_id=commercial_id
    )

@app.route('/nasderm_dashboard')
@login_required
def nasderm_dashboard():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Récupérer les paramètres de filtre
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    commercial_id = request.args.get('commercial')
    
    # Construire la requête de base
    query = Prospection.query.join(User).filter(User.project == 'nasderm')
    
    # Appliquer les filtres
    if date_start:
        query = query.filter(Prospection.date >= date_start)
    if date_end:
        query = query.filter(Prospection.date <= date_end)
    if commercial_id:
        query = query.filter(Prospection.commercial_id == commercial_id)
    
    prospections = query.all()
    
    # Calcul des KPI
    total_revenue = db.session.query(
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price) + func.sum(GilbertSale.quantity * GilbertSale.price)
    ).filter(
        or_(
            NovaPharmaSale.project == 'nasderm',
            GilbertSale.project == 'nasderm'
        )
    ).scalar() or 0
    
    total_visits = len(prospections)
    
    # Récupérer le chiffre d'affaire mensuel pour NASDERM
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('nova_pharma_revenue'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('gilbert_revenue')
    ).outerjoin(GilbertSale, func.strftime('%Y-%m', GilbertSale.date) == func.strftime('%Y-%m', NovaPharmaSale.date)) \
     .filter(or_(NovaPharmaSale.project == 'nasderm', GilbertSale.project == 'nasderm')) \
     .group_by('month').order_by('month').all()
    
    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_nova = [row.nova_pharma_revenue or 0 for row in monthly_revenue]
    monthly_revenue_gilbert = [row.gilbert_revenue or 0 for row in monthly_revenue]
    monthly_revenue_total = [sum(x) for x in zip(monthly_revenue_nova, monthly_revenue_gilbert)]
    
    # Récupérer le classement des commerciaux (Top 5)
    top_5_commerciaux = db.session.query(
        User.username,
        User.zone,
        func.count(Prospection.id).label('nombre_visites')
    ).join(Prospection).filter(User.project == 'nasderm').group_by(User.id).order_by(func.count(Prospection.id).desc()).limit(5).all()
    
    # Récupérer la liste des commerciaux pour NASDERM
    commerciaux = User.query.filter_by(project='nasderm', role='commercial').all()

    return render_template(
        'nasderm_dashboard.html',
        monthly_revenue_labels=monthly_revenue_labels,
        monthly_revenue_nova=monthly_revenue_nova,
        monthly_revenue_gilbert=monthly_revenue_gilbert,
        monthly_revenue_total=monthly_revenue_total,
        top_5_commerciaux=top_5_commerciaux,
        commerciaux=commerciaux,
        prospections=prospections,
        total_revenue=total_revenue,
        total_visits=total_visits,
        date_start=date_start,
        date_end=date_end,
        commercial_id=commercial_id
    )

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    return render_template('admin_dashboard.html')

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    form = UserForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                password=generate_password_hash(form.password.data),
                role=form.role.data,
                zone=form.zone.data,
                project=form.project.data
            )
            db.session.add(user)
            db.session.commit()
            flash('Utilisateur créé avec succès', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la création: {str(e)}", 'error')
    
    return render_template('admin_user_form.html', form=form, title="Ajouter un utilisateur")

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            if form.password.data:
                user.password = generate_password_hash(form.password.data)
            user.role = form.role.data
            user.zone = form.zone.data
            user.project = form.project.data
            db.session.commit()
            flash('Utilisateur mis à jour avec succès', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la mise à jour: {str(e)}", 'error')
    
    return render_template('admin_user_form.html', form=form, title="Modifier l'utilisateur")
    
@app.route('/admin/nova_pharma/sale', methods=['GET', 'POST'])
@login_required
def admin_add_nova_pharma_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in NovaPharmaProduct.query.all()]

    if form.validate_on_submit():
        product = NovaPharmaProduct.query.get(form.product_id.data)
        quantity = form.quantity.data
        entrepot = form.entrepot.data

        sale = NovaPharmaSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=datetime.today().date(),
            commercial_id=current_user.id
        )
        db.session.add(sale)

        # Met à jour le stock
        if entrepot == 'DUOPHARM':
            product.stock_duopharm -= quantity
        elif entrepot == 'LABOREX':
            product.stock_laborex -= quantity
        elif entrepot == 'UBIPHARM':
            product.stock_ubipharm -= quantity
        elif entrepot == 'SODIPHARM':
            product.stock_sodipharm -= quantity

        db.session.commit()
        flash("Vente enregistrée avec succès", "success")
        return redirect(url_for('admin_add_nova_pharma_sale'))

    return render_template('admin_add_nova_pharma_sale.html', form=form)



@app.route('/admin/nova_pharma/product/add', methods=['GET', 'POST'])
@login_required
def add_nova_pharma_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddNovaPharmaProductForm()

    if form.validate_on_submit():
        name = form.name.data
        price = form.price.data

        product = NovaPharmaProduct(
            name=name,
            default_price=price,
            stock_duopharm=0,
            stock_ubipharm=0,
            stock_laborex=0,
            stock_sodipharm=0
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_nova_pharma_product'))

    return render_template('add_nova_pharma_product.html', form=form)

@app.route('/admin/gilbert/sale', methods=['GET', 'POST'])
@login_required
def admin_add_gilbert_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminGilbertSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in GilbertProduct.query.all()]

    if form.validate_on_submit():
        product = GilbertProduct.query.get(form.product_id.data)
        quantity = form.quantity.data

        sale = GilbertSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=datetime.today().date(),
            commercial_id=current_user.id
        )
        db.session.add(sale)

        entrepot = form.entrepot.data
        if entrepot == 'DUOPHARM':
            product.stock_duopharm -= quantity
        elif entrepot == 'LABOREX':
            product.stock_laborex -= quantity
        elif entrepot == 'UBIPHARM':
            product.stock_ubipharm -= quantity
        elif entrepot == 'SODIPHARM':
            product.stock_sodipharm -= quantity

        db.session.commit()
        flash("Vente enregistrée avec succès", "success")
        return redirect(url_for('admin_add_gilbert_sale'))

    return render_template('admin_add_gilbert_sale.html', form=form)


@app.route('/admin/gilbert/product/add', methods=['GET', 'POST'])
@login_required
def add_gilbert_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddGilbertProductForm()
    if form.validate_on_submit():
        product = GilbertProduct(
            name=form.name.data,
            default_price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_gilbert_product'))

    return render_template('add_gilbert_product.html', form=form)


@app.route('/admin/eric_favre/sale', methods=['GET', 'POST'])
@login_required
def admin_add_eric_favre_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminEricFavreSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in EricFavreProduct.query.all()]

    if form.validate_on_submit():
        product = EricFavreProduct.query.get(form.product_id.data)
        quantity = form.quantity.data

        sale = EricFavreSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=datetime.today().date(),
            commercial_id=current_user.id
        )
        db.session.add(sale)

        entrepot = form.entrepot.data
        if entrepot == 'DUOPHARM':
            product.stock_duopharm -= quantity
        elif entrepot == 'LABOREX':
            product.stock_laborex -= quantity
        elif entrepot == 'UBIPHARM':
            product.stock_ubipharm -= quantity
        elif entrepot == 'SODIPHARM':
            product.stock_sodipharm -= quantity

        db.session.commit()
        flash("Vente enregistrée avec succès", "success")
        return redirect(url_for('admin_add_eric_favre_sale'))

    return render_template('admin_add_eric_favre_sale.html', form=form)


@app.route('/admin/eric_favre/product/add', methods=['GET', 'POST'])
@login_required
def add_eric_favre_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddEricFavreProductForm()
    if form.validate_on_submit():
        product = EricFavreProduct(
            name=form.name.data,
            default_price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_eric_favre_product'))

    return render_template('add_eric_favre_product.html', form=form)

@app.route('/admin/trois_chene/sale', methods=['GET', 'POST'])
@login_required
def admin_add_trois_chene_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminTroisCheneSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in TroisCheneProduct.query.all()]

    if form.validate_on_submit():
        product = TroisCheneProduct.query.get(form.product_id.data)
        quantity = form.quantity.data

        sale = TroisCheneSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=datetime.today().date(),
            commercial_id=current_user.id
        )
        db.session.add(sale)

        entrepot = form.entrepot.data
        if entrepot == 'DUOPHARM':
            product.stock_duopharm -= quantity
        elif entrepot == 'LABOREX':
            product.stock_laborex -= quantity
        elif entrepot == 'UBIPHARM':
            product.stock_ubipharm -= quantity
        elif entrepot == 'SODIPHARM':
            product.stock_sodipharm -= quantity

        db.session.commit()
        flash("Vente enregistrée avec succès", "success")
        return redirect(url_for('admin_add_trois_chene_sale'))

    return render_template('admin_add_trois_chene_sale.html', form=form)


@app.route('/admin/trois_chene/product/add', methods=['GET', 'POST'])
@login_required
def add_trois_chene_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddTroisCheneProductForm()
    if form.validate_on_submit():
        product = TroisCheneProduct(
            name=form.name.data,
            default_price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_trois_chene_product'))

    return render_template('add_trois_chene_product.html', form=form)



@app.route('/admin/user/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Utilisateur supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}", 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/plannings')
@login_required
def admin_plannings():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    commerciaux = User.query.filter_by(role='commercial').all()
    return render_template('admin_plannings.html', commerciaux=commerciaux)

@app.route('/admin/planning/<int:commercial_id>')
@login_required
def admin_planning_detail(commercial_id):
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    plannings = Planning.query.filter_by(commercial_id=commercial_id).all()
    commercial = User.query.get(commercial_id)
    return render_template('admin_planning_detail.html', plannings=plannings, commercial=commercial)

@app.route('/admin/prospections')
@login_required
def admin_prospections():
    if current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    prospections = Prospection.query.join(User).order_by(Prospection.date.desc()).all()
    return render_template('admin_prospections.html', prospections=prospections)

@app.route('/eric_favre_sales', methods=['GET', 'POST'])
@login_required
def eric_favre_sales():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = EricFavreProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('eric_favre_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = EricFavreSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasmedic'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Eric Favre enregistrées avec succès', 'success')
        return redirect(url_for('eric_favre_sales'))
    
    return render_template('eric_favre_sales.html', products=products)

@app.route('/trois_chene_sales', methods=['GET', 'POST'])
@login_required
def trois_chene_sales():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = TroisCheneProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('trois_chene_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = TroisCheneSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasmedic'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes 3 Chênes Pharma enregistrées avec succès', 'success')
        return redirect(url_for('trois_chene_sales'))
    
    return render_template('trois_chene_sales.html', products=products)

@app.route('/nova_pharma_sales', methods=['GET', 'POST'])
@login_required
def nova_pharma_sales():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = NovaPharmaProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('nova_pharma_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = NovaPharmaSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Nova Pharma enregistrées avec succès', 'success')
        return redirect(url_for('nova_pharma_sales'))
    
    return render_template('nova_pharma_sales.html', products=products)

@app.route('/gilbert_sales', methods=['GET', 'POST'])
@login_required
def gilbert_sales():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = GilbertProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('gilbert_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = GilbertSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes Gilbert enregistrées avec succès', 'success')
        return redirect(url_for('gilbert_sales'))
    
    return render_template('gilbert_sales.html', products=products)

@app.route('/monthly_revenue_nasmedic')
@login_required
def monthly_revenue_nasmedic():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('eric_favre_revenue'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('trois_chene_revenue')
    ).outerjoin(TroisCheneSale, func.strftime('%Y-%m', TroisCheneSale.date) == func.strftime('%Y-%m', EricFavreSale.date)) \
     .filter(or_(EricFavreSale.project == 'nasmedic', TroisCheneSale.project == 'nasmedic')) \
     .group_by('month').order_by('month').all()
    
    total = 1
    return render_template('monthly_revenue_nasmedic.html', monthly_revenue=monthly_revenue, total=total)

@app.route('/monthly_revenue_nasderm')
@login_required
def monthly_revenue_nasderm():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    # Créer un alias pour GilbertSale
    gilbert_sale_alias = aliased(GilbertSale)
    
    # Requête modifiée pour l'utilisation de l'alias
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('nova_pharma_revenue'),
        func.sum(gilbert_sale_alias.quantity * gilbert_sale_alias.price).label('gilbert_revenue')
    ).outerjoin(gilbert_sale_alias, func.strftime('%Y-%m', gilbert_sale_alias.date) == func.strftime('%Y-%m', NovaPharmaSale.date)) \
     .filter(or_(NovaPharmaSale.project == 'nasderm', gilbert_sale_alias.project == 'nasderm')) \
     .group_by('month').order_by('month').all()
    
    total = 1
    return render_template('monthly_revenue_nasderm.html', monthly_revenue=monthly_revenue, total=total)

@app.route('/monthly_revenue_detail_nasmedic/<month>')
@login_required
def monthly_revenue_detail_nasmedic(month):
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    eric_favre_sales = db.session.query(
        EricFavreProduct.name,
        func.sum(EricFavreSale.quantity).label('total_quantity'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('total_revenue')
    ).join(EricFavreSale).filter(
        func.strftime('%Y-%m', EricFavreSale.date) == month,
        EricFavreSale.project == 'nasmedic'
    ).group_by(EricFavreProduct.name).all()
    
    trois_chene_sales = db.session.query(
        TroisCheneProduct.name,
        func.sum(TroisCheneSale.quantity).label('total_quantity'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('total_revenue')
    ).join(TroisCheneSale).filter(
        func.strftime('%Y-%m', TroisCheneSale.date) == month,
        TroisCheneSale.project == 'nasmedic'
    ).group_by(TroisCheneProduct.name).all()
    
    return render_template('monthly_revenue_detail_nasmedic.html', 
                         month=month, 
                         eric_favre_sales=eric_favre_sales, 
                         trois_chene_sales=trois_chene_sales)

@app.route('/monthly_revenue_detail_nasderm/<month>')
@login_required
def monthly_revenue_detail_nasderm(month):
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    nova_pharma_sales = db.session.query(
        NovaPharmaProduct.name,
        func.sum(NovaPharmaSale.quantity).label('total_quantity'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('total_revenue')
    ).join(NovaPharmaSale).filter(
        func.strftime('%Y-%m', NovaPharmaSale.date) == month,
        NovaPharmaSale.project == 'nasderm'
    ).group_by(NovaPharmaProduct.name).all()

    gilbert_sales = db.session.query(
        GilbertProduct.name,
        func.sum(GilbertSale.quantity).label('total_quantity'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('total_revenue')
    ).join(GilbertSale).filter(
        func.strftime('%Y-%m', GilbertSale.date) == month,
        GilbertSale.project == 'nasderm'
    ).group_by(GilbertProduct.name).all()

    return render_template('monthly_revenue_detail_nasderm.html', 
                         month=month, 
                         nova_pharma_sales=nova_pharma_sales, 
                         gilbert_sales=gilbert_sales)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie', 'success')
    return redirect(url_for('home'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

def create_initial_data():
    with app.app_context():
        db.create_all()
        
        # Créer les utilisateurs initiaux
        if not User.query.filter_by(username="Anna Diallo").first():
            admin = User(
                username="Anna Diallo",
                password=generate_password_hash("admin123", method="pbkdf2:sha256"),
                role="admin",
                zone=None,
                project='nasmedic'
            )
            db.session.add(admin)
        
        # Commerciaux NASMEDIC
        commerciaux_nasmedic = [
            ("KHALIFA DIOP", "khalifa123", "CENTRE VILLE", 'nasmedic'),
            ("AMADOU DEME", "amadou123", "Banlieue 1", 'nasmedic'),
            ("MBAYE NDOYE", "mbaye123", "THIES", 'nasmedic'),
            ("MEDINA K NDIAYE", "medina123", "ZONES INTERMEDIAIRE 2", 'nasmedic'),
            ("MARIE LOUISE", "marie123", "MBOUR", 'nasmedic'),
            ("CHEIKH DIOP", "cheikh123", "ZONES INTERMEDIAIRE 1", 'nasmedic'),
            ("MASSAMBA MBAYE", "massamba123", "Banlieue 2", 'nasmedic'),
            ("LAMINE THIOUB", "lamine123", "REGION DE DIOURBEL", 'nasmedic'),
        ]
        
        for username, password, zone, project in commerciaux_nasmedic:
            if not User.query.filter_by(username=username).first():
                db.session.add(User(
                    username=username,
                    password=generate_password_hash(password, method="pbkdf2:sha256"),
                    role="commercial",
                    zone=zone,
                    project=project
                ))
        
        # Commerciaux NASDERM
        commerciaux_nasderm = [
            ("FAMA DIOP", "fama123", "THIES", 'nasderm'),
            ("MARIE JEANNE DIOUF", "marie123", "Banlieue 1", 'nasderm'),
            ("ASTOU MANA MBENGUE", "astou123", "DAKAR", 'nasderm'),
            ("HONORINE", "honorine123", "ZONES INTERMEDIAIRE 2", 'nasderm'),
            ("MIJO", "mijo123", "MBOUR", 'nasderm'),
            ("HELENE FAYE", "helene123", "ZONES INTERMEDIAIRE 1", 'nasderm'),
            ("ADJARA CISSÉ", "adjara123", "Banlieue 2", 'nasderm'),
            ("KHAR FALL", "khar123", "REGION DE DIOURBEL", 'nasderm'),
            ("KHADY SOW", "khady123", "REGION DE DIOURBEL", 'nasderm'),
        ]
        
        for username, password, zone, project in commerciaux_nasderm:
            if not User.query.filter_by(username=username).first():
                db.session.add(User(
                    username=username,
                    password=generate_password_hash(password, method="pbkdf2:sha256"),
                    role="commercial",
                    zone=zone,
                    project=project
                ))
        
        # Produits Nova Pharma
        nova_pharma_products = [
            ("HYFAC GEL NETTOYANT FLC 150ML", 3.5),
            ("HYFAC GEL NETTOYANT TB 300ML", 3.5),
            # ... (liste complète des produits)
        ]
        
        for name, price in nova_pharma_products:
            if not NovaPharmaProduct.query.filter_by(name=name).first():
                db.session.add(NovaPharmaProduct(
                    name=name,
                    default_price=price
                ))
        
        # Produits Gilbert
        gilbert_products = [
            ("ELLE TEST BTE DE 1 TEST GROSSESSE", 3.5),
            ("MOUSTIDOSE SPRAY REPULSIF ZONE INFESTEES IR3535 +12M  100ML", 3.5),
            # ... (liste complète des produits)
        ]
        
        for name, price in gilbert_products:
            if not GilbertProduct.query.filter_by(name=name).first():
                db.session.add(GilbertProduct(
                    name=name,
                    default_price=price
                ))
        
        # Produits Eric Favre
        eric_favre_products = [
            ("Chronoerect", 3.58),
            ("Special Kid calcium", 2.65),
            # ... (liste complète des produits)
        ]
        
        for name, price in eric_favre_products:
            if not EricFavreProduct.query.filter_by(name=name).first():
                db.session.add(EricFavreProduct(
                    name=name,
                    default_price=price
                ))
        
        # Produits 3 Chênes Pharma
        trois_chene_products = [
            ("ASTHE 1000", 6.05),
            ("BOIS BANDE", 3.45),
            # ... (liste complète des produits)
        ]
        
        for name, price in trois_chene_products:
            if not TroisCheneProduct.query.filter_by(name=name).first():
                db.session.add(TroisCheneProduct(
                    name=name,
                    default_price=price
                ))
        
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_initial_data()
    app.run(debug=True)
