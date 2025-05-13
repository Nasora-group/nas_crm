# app.py
from flask import Flask
from extensions import db  # On importe db depuis extensions.py
from openpyxl import Workbook
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Exemple avec SQLite
db.init_app(app)  # On relie db à l'application Flask

# On importe les modèles APRÈS avoir créé app et db
from models import User, Prospection, NovaPharmaProduct, GilbertProduct, EricFavreProduct, TroisCheneProduct, NovaPharmaSale, GilbertSale, EricFavreSale, TroisCheneSale, Planning

# Le reste de ton code (routes, etc.)
from flask import Flask, render_template, request, redirect, abort, url_for, flash, send_file
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
from sqlalchemy import extract

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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/create-admin')
def create_admin():
    from werkzeug.security import generate_password_hash
    from models import User
    from extensions import db

    if User.query.filter_by(username='admin').first():
        return "Admin déjà créé."

    hashed_pw = generate_password_hash("admin123")
    admin = User(username="admin", password=hashed_pw, role="admin", project="nasmedic")

    db.session.add(admin)
    db.session.commit()
    return "Admin créé avec succès."


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

# Dashboard Commercial
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        form = ProspectionForm()
        today = date.today()

        # Vérifier que current_user.id n'est pas None
        if not current_user.is_authenticated or current_user.id is None:
            flash("Utilisateur non authentifié", "danger")
            return redirect(url_for('login'))

        # Charger les prospections de l'utilisateur
        prospections = Prospection.query.filter(
            Prospection.commercial_id == current_user.id,
            extract('month', Prospection.date) == today.month,
            extract('year', Prospection.date) == today.year
        ).all()

        produits_presentes_count = sum(1 for p in prospections if p.produits_presentes)
        taux_conversion = (
            sum(1 for p in prospections if p.produits_prescrits) / produits_presentes_count * 100
        ) if produits_presentes_count > 0 else 0

        return render_template('dashboard.html',
                               form=form,
                               prospections=prospections,
                               produits_presentes_count=produits_presentes_count,
                               taux_conversion=round(taux_conversion, 2))
    except Exception as e:
        print("Erreur lors du chargement du tableau de bord:", e)
        flash(f"Erreur lors du chargement du tableau de bord : {e}", "danger")
        return redirect(url_for('login'))
        
        
@app.route('/admin/commerciaux')
@login_required
def liste_commerciaux():
    if current_user.role != 'admin':
        flash("Accès réservé à l'administrateur.", "danger")
        return redirect(url_for('dashboard'))
    
    commerciaux = User.query.filter_by(role='commercial').all()
    return render_template('admin_commerciaux.html', commerciaux=commerciaux)

# Nouvelle fonction pour calculer le CA mensuel par commercial
@app.route('/api/ca_mensuel/<int:commercial_id>')
@login_required
def ca_mensuel_commercial(commercial_id):
    if current_user.role != 'admin' and current_user.id != commercial_id:
        abort(403)
    
    # Calcul pour NASMEDIC
    eric_ca = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('mois'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('ca')
    ).filter(
        EricFavreSale.commercial_id == commercial_id
    ).group_by('mois').all()

    trois_chene_ca = db.session.query(
        func.strftime('%Y-%m', TroisCheneSale.date).label('mois'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('ca')
    ).filter(
        TroisCheneSale.commercial_id == commercial_id
    ).group_by('mois').all()

    # Calcul pour NASDERM
    nova_ca = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('mois'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('ca')
    ).filter(
        NovaPharmaSale.commercial_id == commercial_id
    ).group_by('mois').all()

    gilbert_ca = db.session.query(
        func.strftime('%Y-%m', GilbertSale.date).label('mois'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('ca')
    ).filter(
        GilbertSale.commercial_id == commercial_id
    ).group_by('mois').all()

    # Fusion des résultats
    results = {}
    for ca in [eric_ca, trois_chene_ca, nova_ca, gilbert_ca]:
        for row in ca:
            if row.mois not in results:
                results[row.mois] = {'eric_favre': 0, 'trois_chene': 0, 'nova_pharma': 0, 'gilbert': 0, 'total': 0}
            if ca == eric_ca:
                results[row.mois]['eric_favre'] = float(row.ca or 0)
            elif ca == trois_chene_ca:
                results[row.mois]['trois_chene'] = float(row.ca or 0)
            elif ca == nova_ca:
                results[row.mois]['nova_pharma'] = float(row.ca or 0)
            elif ca == gilbert_ca:
                results[row.mois]['gilbert'] = float(row.ca or 0)
            results[row.mois]['total'] = sum([
                results[row.mois]['eric_favre'],
                results[row.mois]['trois_chene'],
                results[row.mois]['nova_pharma'],
                results[row.mois]['gilbert']
            ])

    return jsonify(results)

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

@app.route('/prospection/list')
@login_required
def prospection_list():
    """Affiche la liste des prospections du commercial"""
    prospections = Prospection.query.filter_by(commercial_id=current_user.id).order_by(Prospection.date.desc()).all()
    return render_template('prospection_list.html', prospections=prospections)

@app.route('/prospection/<int:prospection_id>')
@login_required
def voir_prospection(prospection_id):
    """Affiche les détails d'une prospection"""
    prospection = Prospection.query.get_or_404(prospection_id)
    if prospection.commercial_id != current_user.id and current_user.role != 'admin':
        abort(403)
    return render_template('voir_prospection.html', prospection=prospection)

@app.route('/edit_prospection/<int:prospection_id>', methods=['GET', 'POST'])
@login_required
def edit_prospection(prospection_id):
    prospection = Prospection.query.get_or_404(prospection_id)
    
    # Vérification des droits
    if current_user.id != prospection.commercial_id and current_user.role != 'admin':
        abort(403)
    
    form = ProspectionForm(obj=prospection)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(prospection)
            db.session.commit()
            flash('Prospection modifiée avec succès', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la modification: {str(e)}", 'error')
    
    return render_template('edit_prospection.html', form=form, prospection=prospection)

@app.route('/ventes')
@login_required
def ventes():
    """Route générale pour les ventes - Redirige vers la page appropriée selon le projet"""
    if current_user.project == 'nasmedic':
        # Pour NASMEDIC: Eric Favre et 3 Chênes
        return render_template('ventes_nasmedic.html', 
                            ventes_eric=EricFavreSale.query.filter_by(commercial_id=current_user.id).all(),
                            ventes_trois=TroisCheneSale.query.filter_by(commercial_id=current_user.id).all())
    else:
        # Pour NASDERM: Nova Pharma et Gilbert
        return render_template('ventes_nasderm.html',
                            ventes_nova=NovaPharmaSale.query.filter_by(commercial_id=current_user.id).all(),
                            ventes_gilbert=GilbertSale.query.filter_by(commercial_id=current_user.id).all())

@app.route('/delete_prospection/<int:prospection_id>')
@login_required
def delete_prospection(prospection_id):
    prospection = Prospection.query.get_or_404(prospection_id)
    
    if current_user.id != prospection.commercial_id and current_user.role != 'admin':
        abort(403)
    
    try:
        db.session.delete(prospection)
        db.session.commit()
        flash('Prospection supprimée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}", 'error')
    
    return redirect(url_for('dashboard'))
    
@app.route('/edit_planning/<int:planning_id>', methods=['GET', 'POST'])
@login_required
def edit_planning(planning_id):
    planning = Planning.query.get_or_404(planning_id)
    
    if current_user.id != planning.commercial_id and current_user.role != 'admin':
        abort(403)
    
    form = PlanningForm(obj=planning)
    
    if form.validate_on_submit():
        try:
            # Traitement similaire à la création
            details_dict = request.form.to_dict()
            jours = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
            periodes = ['matin', 'soir']

            for jour in jours:
                for periode in periodes:
                    field_name = f"{jour}_{periode}"
                    structures = getattr(form, field_name).data
                    results = []
                    for structure in structures:
                        key = f"{field_name}_{structure.lower().replace(' ', '_')}"
                        detail = details_dict.get(key, '').strip()
                        results.append(f"{structure} - {detail}")
                    setattr(planning, field_name, "\n".join(results))
            
            db.session.commit()
            flash('Planning modifié avec succès', 'success')
            return redirect(url_for('visualiser_planning'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la modification: {str(e)}", 'error')
    
    return render_template('edit_planning.html', form=form, planning=planning)

@app.route('/set_target', methods=['GET', 'POST'])
@login_required
def set_target():
    form = SalesTargetForm()
    if form.validate_on_submit():
        existing = SalesTarget.query.filter_by(
            commercial_id=current_user.id,
            month=form.month.data,
            year=form.year.data
        ).first()
        
        if existing:
            existing.target_amount = form.target_amount.data
        else:
            target = SalesTarget(
                commercial_id=current_user.id,
                month=form.month.data,
                year=form.year.data,
                target_amount=form.target_amount.data
            )
            db.session.add(target)
        
        db.session.commit()
        flash('Objectif enregistré avec succès', 'success')
        return redirect(url_for('my_stats'))
    
    return render_template('set_target.html', form=form)

@app.route('/export/my_data')
@login_required
def export_my_data():
    prospections = Prospection.query.filter_by(commercial_id=current_user.id).all()
    
    if current_user.project == 'nasmedic':
        sales_eric = EricFavreSale.query.filter_by(commercial_id=current_user.id).all()
        sales_trois = TroisCheneSale.query.filter_by(commercial_id=current_user.id).all()
        sales_data = [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'Eric Favre',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_eric
        ] + [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': '3 Chênes',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_trois
        ]
    else:
        sales_nova = NovaPharmaSale.query.filter_by(commercial_id=current_user.id).all()
        sales_gilbert = GilbertSale.query.filter_by(commercial_id=current_user.id).all()
        sales_data = [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'Nova Pharma',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_nova
        ] + [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'Gilbert',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_gilbert
        ]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([{
            'Date': p.date.strftime('%Y-%m-%d'),
            'Client': p.nom_client,
            'Structure': p.structure,
            'Spécialité': p.specialite,
            'Téléphone': p.telephone,
            'Produits présentés': p.produits_presentes,
            'Produits prescrits': p.produits_prescrits
        } for p in prospections]).to_excel(writer, sheet_name='Prospections', index=False)
        
        pd.DataFrame(sales_data).to_excel(writer, sheet_name='Ventes', index=False)
        
        stats = {
            'Mois': datetime.now().strftime('%Y-%m'),
            'Visites': len(prospections),
            'Produits présentés': sum(1 for p in prospections if p.produits_presentes),
            'Produits prescrits': sum(1 for p in prospections if p.produits_prescrits),
            'CA total': sum(sale['Total'] for sale in sales_data)
        }
        pd.DataFrame([stats]).to_excel(writer, sheet_name='Statistiques', index=False)
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'export_{current_user.username}_{datetime.now().date()}.xlsx'
    )
  
@app.route('/notifications')
@login_required
def notifications():
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    read = Notification.query.filter_by(user_id=current_user.id, is_read=True).order_by(Notification.created_at.desc()).limit(10).all()
    return render_template('notifications.html', unread=unread, read=read)

@app.route('/notifications/mark_as_read/<int:notification_id>')
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    return redirect(url_for('notifications'))
    
   
@app.route('/my_stats')
@login_required
def my_stats():
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    # Récupérer les prospections
    prospections = Prospection.query.filter(
        Prospection.commercial_id == current_user.id,
        Prospection.date >= month_start
    ).all()
    
    # Calculer les stats de prospection
    prospection_stats = {
        'nb_visites': len(prospections),
        'produits_presentes': sum(1 for p in prospections if p.produits_presentes),
        'produits_prescrits': sum(1 for p in prospections if p.produits_prescrits)
    }
    
    if prospection_stats['produits_presentes'] > 0:
        prospection_stats['taux_conversion'] = (prospection_stats['produits_prescrits'] / prospection_stats['produits_presentes']) * 100
    else:
        prospection_stats['taux_conversion'] = 0
    
    # Calculer le CA
    ca_stats = current_user.get_monthly_ca(today.year, today.month)
    
    return render_template('my_stats.html', 
                         prospection_stats=prospection_stats,
                         ca_stats=ca_stats)

@app.route('/visualiser_planning')
@login_required
def visualiser_planning():
    plannings = Planning.query.filter_by(commercial_id=current_user.id).all()
    return render_template('visualiser_planning.html', plannings=plannings)


@app.route("/admin/prospection/<int:prospection_id>")
@login_required
def voir_prospection_admin(prospection_id):
    if current_user.role != 'admin':
        abort(403)
    
    prospection = Prospection.query.get_or_404(prospection_id)
    commercial = User.query.get(prospection.commercial_id)
    
    return render_template(
        "admin/voir_prospection_admin.html",
        prospection=prospection,
        commercial=commercial
    )


@app.route("/admin/prospections/<int:commercial_id>")
@login_required
def prospections_commercial(commercial_id):
    commercial = User.query.get_or_404(commercial_id)
    prospections = Prospection.query.filter_by(commercial_id=commercial.id).order_by(Prospection.date.desc()).all()
    return render_template("admin/prospections_par_commercial.html", commercial=commercial, prospections=prospections)

@app.route("/admin/export_prospections/<int:commercial_id>")
@login_required
def export_prospections(commercial_id):
    commercial = User.query.get_or_404(commercial_id)
    prospections = Prospection.query.filter_by(commercial_id=commercial.id).all()

    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Nom Client", "Structure", "Spécialité", "Téléphone", "Profil", "Produits Présentés", "Produits Prescrits"])

    for p in prospections:
        ws.append([
            p.date.strftime('%d/%m/%Y'),
            p.nom_client, p.structure, p.specialite, p.telephone,
            p.profils_prospect, p.produits_presentes, p.produits_prescrits
        ])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    filename = f"Prospections_{commercial.username}.xlsx"

    return send_file(file_stream, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    
@app.route('/admin/prospections/filter', methods=['GET'])
@login_required
def filter_prospections():
    if current_user.role != 'admin':
        abort(403)
    
    commercial_id = request.args.get('commercial_id')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    
    query = Prospection.query.join(User)
    
    if commercial_id:
        query = query.filter(Prospection.commercial_id == commercial_id)
    if date_start:
        query = query.filter(Prospection.date >= date_start)
    if date_end:
        query = query.filter(Prospection.date <= date_end)
    
    prospections = query.order_by(Prospection.date.desc()).all()
    commerciaux = User.query.filter_by(role='commercial').all()
    
    return render_template('admin_prospections_filter.html',
                         prospections=prospections,
                         commerciaux=commerciaux,
                         commercial_id=commercial_id,
                         date_start=date_start,
                         date_end=date_end)

@app.route('/admin/export_filtered_prospections')
@login_required
def export_filtered_prospections():
    if current_user.role != 'admin':
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    commercial_id = request.args.get('commercial_id')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    
    query = Prospection.query.join(User)
    
    if commercial_id:
        query = query.filter(Prospection.commercial_id == commercial_id)
    if date_start:
        query = query.filter(Prospection.date >= date_start)
    if date_end:
        query = query.filter(Prospection.date <= date_end)
    
    prospections = query.order_by(Prospection.date.desc()).all()
    
    data = [{
        "Date": p.date.strftime("%Y-%m-%d"),
        "Nom du client": p.nom_client,
        "Structure": p.structure,
        "Spécialité": p.specialite,
        "Téléphone": p.telephone,
        "Profil prospect": p.profils_prospect,
        "Produits présentés": p.produits_presentes,
        "Produits prescrits": p.produits_prescrits,
        "Commercial": p.commercial.username
    } for p in prospections]

    df = pd.DataFrame(data)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Prospections_filtrees', index=False)
    writer.close()
    output.seek(0)
    
    filename = 'prospections_filtrees.xlsx'
    if commercial_id:
        commercial = User.query.get(commercial_id)
        filename = f'prospections_{commercial.username}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/saisie_planning', methods=['GET', 'POST'])
@login_required
def saisie_planning():
    form = PlanningForm()
    if form.validate_on_submit():
        details_dict = request.form.to_dict()
        jours = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
        periodes = ['matin', 'soir']

        for jour in jours:
            for periode in periodes:
                # Récupération des structures sélectionnées (ex: ['PHARMACIE', 'CLINIQUE'])
                field_name = f"{jour}_{periode}"
                structures = getattr(form, field_name).data  # liste

                results = []
                for structure in structures:
                    key = f"{field_name}_{structure.lower().replace(' ', '_')}"  # ex: lundi_matin_centre_de_sante
                    detail = details_dict.get(key, '').strip()
                    results.append(f"{structure} - {detail}")

                formatted_value = "\n".join(results)

                setattr(form, field_name, formatted_value)  # on remplace la liste par une string

        # Création du planning
        planning = Planning(
            commercial_id=current_user.id,
            date=form.date.data,
            lundi_matin=form.lundi_matin,
            lundi_soir=form.lundi_soir,
            mardi_matin=form.mardi_matin,
            mardi_soir=form.mardi_soir,
            mercredi_matin=form.mercredi_matin,
            mercredi_soir=form.mercredi_soir,
            jeudi_matin=form.jeudi_matin,
            jeudi_soir=form.jeudi_soir,
            vendredi_matin=form.vendredi_matin,
            vendredi_soir=form.vendredi_soir,
            samedi_matin=form.samedi_matin,
            samedi_soir=form.samedi_soir,
            dimanche_matin=form.dimanche_matin,
            dimanche_soir=form.dimanche_soir
        )

        db.session.add(planning)
        db.session.commit()
        flash('Planning enregistré avec succès.', 'success')
        return redirect(url_for('visualiser_planning'))

    return render_template('saisie_planning.html', form=form)

    

@app.route('/admin/export_prospections/<int:commercial_id>')
@login_required
def export_prospections_commercial(commercial_id):
    if current_user.role != 'admin':
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    commercial = User.query.get_or_404(commercial_id)
    prospections = Prospection.query.filter_by(commercial_id=commercial_id)\
                                  .order_by(Prospection.date.desc())\
                                  .all()
    
    data = [{
        "Date": p.date.strftime("%Y-%m-%d"),
        "Nom du client": p.nom_client,
        "Structure": p.structure,
        "Spécialité": p.specialite,
        "Téléphone": p.telephone,
        "Profil prospect": p.profils_prospect,
        "Produits présentés": p.produits_presentes,
        "Produits prescrits": p.produits_prescrits
    } for p in prospections]

    df = pd.DataFrame(data)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name=f'Prospections_{commercial.username}', index=False)
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'prospections_{commercial.username}.xlsx'
    )

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
        sale_date = form.sale_date.data

        sale = NovaPharmaSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=sale_date,
            commercial_id=current_user.id
        )
        db.session.add(sale)

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
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = GilbertSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=sale_date,
            commercial_id=current_user.id
        )
        db.session.add(sale)

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
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = EricFavreSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=sale_date,
            commercial_id=current_user.id
        )
        db.session.add(sale)

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
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = TroisCheneSale(
            product_id=product.id,
            quantity=quantity,
            price=product.default_price * quantity,
            date=sale_date,
            commercial_id=current_user.id
        )
        db.session.add(sale)

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

    monthly_revenue_raw = db.session.query(
        func.strftime('%Y-%m', EricFavreSale.date).label('month'),
        func.sum(EricFavreSale.quantity * EricFavreSale.price).label('eric_favre_revenue'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('trois_chene_revenue')
    ).outerjoin(
        TroisCheneSale, func.strftime('%Y-%m', TroisCheneSale.date) == func.strftime('%Y-%m', EricFavreSale.date)
    ).filter(
        or_(EricFavreSale.project == 'nasmedic', TroisCheneSale.project == 'nasmedic')
    ).group_by('month').order_by('month').all()

    monthly_revenue = []
    total = 0.0
    for row in monthly_revenue_raw:
        eric = float(row.eric_favre_revenue or 0)
        trois = float(row.trois_chene_revenue or 0)
        total += eric + trois
        monthly_revenue.append({
            'month': row.month,
            'eric_favre': f"{eric:.2f}",
            'trois_chene': f"{trois:.2f}",
            'total': f"{eric + trois:.2f}"
        })

    return render_template('monthly_revenue_nasmedic.html', monthly_revenue=monthly_revenue, total=f"{total:.2f}")


@app.route('/monthly_revenue_nasderm')
@login_required
def monthly_revenue_nasderm():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    gilbert_sale_alias = aliased(GilbertSale)

    monthly_revenue_raw = db.session.query(
        func.strftime('%Y-%m', NovaPharmaSale.date).label('month'),
        func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price).label('nova_pharma_revenue'),
        func.sum(gilbert_sale_alias.quantity * gilbert_sale_alias.price).label('gilbert_revenue')
    ).outerjoin(
        gilbert_sale_alias, func.strftime('%Y-%m', gilbert_sale_alias.date) == func.strftime('%Y-%m', NovaPharmaSale.date)
    ).filter(
        or_(NovaPharmaSale.project == 'nasderm', gilbert_sale_alias.project == 'nasderm')
    ).group_by('month').order_by('month').all()

    monthly_revenue = []
    total = 0.0
    for row in monthly_revenue_raw:
        nova = float(row.nova_pharma_revenue or 0)
        gilbert = float(row.gilbert_revenue or 0)
        total += nova + gilbert
        monthly_revenue.append({
            'month': row.month,
            'nova_pharma': f"{nova:.2f}",
            'gilbert': f"{gilbert:.2f}",
            'total': f"{nova + gilbert:.2f}"
        })

    return render_template('monthly_revenue_nasderm.html', monthly_revenue=monthly_revenue, total=f"{total:.2f}")

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
    ).join(EricFavreProduct, EricFavreSale.product_id == EricFavreProduct.id).filter(
        func.strftime('%Y-%m', EricFavreSale.date) == month,
        EricFavreSale.project == 'nasmedic'
    ).group_by(EricFavreProduct.name).all()

    trois_chene_sales = db.session.query(
        TroisCheneProduct.name,
        func.sum(TroisCheneSale.quantity).label('total_quantity'),
        func.sum(TroisCheneSale.quantity * TroisCheneSale.price).label('total_revenue')
    ).join(TroisCheneProduct, TroisCheneSale.product_id == TroisCheneProduct.id).filter(
        func.strftime('%Y-%m', TroisCheneSale.date) == month,
        TroisCheneSale.project == 'nasmedic'
    ).group_by(TroisCheneProduct.name).all()

    return render_template(
        'monthly_revenue_detail_nasmedic.html',
        month=month,
        eric_favre_sales=eric_favre_sales,
        trois_chene_sales=trois_chene_sales
    )


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
    ).join(NovaPharmaProduct, NovaPharmaSale.product_id == NovaPharmaProduct.id).filter(
        func.strftime('%Y-%m', NovaPharmaSale.date) == month,
        NovaPharmaSale.project == 'nasderm'
    ).group_by(NovaPharmaProduct.name).all()

    gilbert_sales = db.session.query(
        GilbertProduct.name,
        func.sum(GilbertSale.quantity).label('total_quantity'),
        func.sum(GilbertSale.quantity * GilbertSale.price).label('total_revenue')
    ).join(GilbertProduct, GilbertSale.product_id == GilbertProduct.id).filter(
        func.strftime('%Y-%m', GilbertSale.date) == month,
        GilbertSale.project == 'nasderm'
    ).group_by(GilbertProduct.name).all()

    return render_template(
        'monthly_revenue_detail_nasderm.html',
        month=month,
        nova_pharma_sales=nova_pharma_sales,
        gilbert_sales=gilbert_sales
    )



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

@app.route('/init-data')
def init_data():
    try:
        create_initial_data()
        return "Données initiales créées avec succès"
    except Exception as e:
        return f"Erreur lors de la création des données : {e}"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_initial_data()
    app.run(debug=True)
