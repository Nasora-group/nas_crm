# app.py
from flask import Flask
from extensions import db  # On importe db depuis extensions.py
from openpyxl import Workbook
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Exemple avec SQLite
db.init_app(app)  # On relie db à l'application Flask

# On importe les modèles APRÈS avoir créé app et db
from models import User, Prospection, HRAProduct, ramopharmaProduct, farmalfaProduct, opalaProduct, HRASale, ramopharmaSale, farmalfaSale, opalaSale, Planning

# Le reste de ton code (routes, etc.)
from flask import Flask, render_template, request, redirect, abort, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pandas as pd
from io import BytesIO
from forms import ProspectionForm, LoginForm, DownloadExcelForm, HRASalesForm, ramopharmaSalesForm, farmalfaSalesForm, opalaSalesForm, PlanningForm, UserForm, AdminfarmalfaSaleForm, AdminramopharmaSaleForm, AdminopalaSaleForm, AddfarmalfaProductForm, AddramopharmaProductForm, AddopalaProductForm, AdminSaleForm, AddHRAProductForm
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, and_
import logging
from sqlalchemy.orm import aliased
from sqlalchemy import or_
from models import db, User, Prospection, HRAProduct, ramopharmaProduct, farmalfaProduct, opalaProduct, HRASale, ramopharmaSale, farmalfaSale, opalaSale, Planning
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
    farmalfa_ca = db.session.query(
        func.strftime('%Y-%m', farmalfaSale.date).label('mois'),
        func.sum(farmalfaSale.quantity * farmalfaSale.price).label('ca')
    ).filter(
        farmalfaSale.commercial_id == commercial_id
    ).group_by('mois').all()

    trois_chene_ca = db.session.query(
        func.strftime('%Y-%m', opalaSale.date).label('mois'),
        func.sum(opalaSale.quantity * opalaSale.price).label('ca')
    ).filter(
        opalaSale.commercial_id == commercial_id
    ).group_by('mois').all()

    # Calcul pour NASDERM
    nova_ca = db.session.query(
        func.strftime('%Y-%m', HRASale.date).label('mois'),
        func.sum(HRASale.quantity * HRASale.price).label('ca')
    ).filter(
        HRASale.commercial_id == commercial_id
    ).group_by('mois').all()

    ramopharma_ca = db.session.query(
        func.strftime('%Y-%m', ramopharmaSale.date).label('mois'),
        func.sum(ramopharmaSale.quantity * ramopharmaSale.price).label('ca')
    ).filter(
        ramopharmaSale.commercial_id == commercial_id
    ).group_by('mois').all()

    # Fusion des résultats
    results = {}
    for ca in [farmalfa_ca, trois_chene_ca, nova_ca, ramopharma_ca]:
        for row in ca:
            if row.mois not in results:
                results[row.mois] = {'farmalfa_favre': 0, 'trois_chene': 0, 'nova_pharma': 0, 'ramopharma': 0, 'total': 0}
            if ca == farmalfa_ca:
                results[row.mois]['farmalfa_favre'] = float(row.ca or 0)
            elif ca == trois_chene_ca:
                results[row.mois]['trois_chene'] = float(row.ca or 0)
            elif ca == nova_ca:
                results[row.mois]['nova_pharma'] = float(row.ca or 0)
            elif ca == ramopharma_ca:
                results[row.mois]['ramopharma'] = float(row.ca or 0)
            results[row.mois]['total'] = sum([
                results[row.mois]['farmalfa_favre'],
                results[row.mois]['trois_chene'],
                results[row.mois]['nova_pharma'],
                results[row.mois]['ramopharma']
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
        # Pour NASMEDIC: farmalfa et 3 Chênes
        return render_template('ventes_nasmedic.html', 
                            ventes_farmalfa=farmalfaSale.query.filter_by(commercial_id=current_user.id).all(),
                            ventes_trois=opalaSale.query.filter_by(commercial_id=current_user.id).all())
    else:
        # Pour NASDERM: HRA et ramopharma
        return render_template('ventes_nasderm.html',
                            ventes_nova=HRASale.query.filter_by(commercial_id=current_user.id).all(),
                            ventes_ramopharma=ramopharmaSale.query.filter_by(commercial_id=current_user.id).all())

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
        sales_farmalfa = farmalfaSale.query.filter_by(commercial_id=current_user.id).all()
        sales_trois = opalaSale.query.filter_by(commercial_id=current_user.id).all()
        sales_data = [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'farmalfa',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_farmalfa
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
        sales_nova = HRASale.query.filter_by(commercial_id=current_user.id).all()
        sales_ramopharma = ramopharmaSale.query.filter_by(commercial_id=current_user.id).all()
        sales_data = [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'HRA',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_nova
        ] + [
            {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'Type': 'ramopharma',
                'Produit': sale.product.name,
                'Quantité': sale.quantity,
                'Prix Unitaire': sale.price / sale.quantity,
                'Total': sale.price
            } for sale in sales_ramopharma
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
        ventes_farmalfa = farmalfaSale.query.filter_by(commercial_id=current_user.id).all()
        ventes_trois = opalaSale.query.filter_by(commercial_id=current_user.id).all()
        return render_template('mes_ventes.html', ventes_farmalfa=ventes_farmalfa, ventes_trois=ventes_trois)

    elif current_user.project == 'nasderm':
        ventes_nova = HRASale.query.filter_by(commercial_id=current_user.id).all()
        ventes_ramopharma = ramopharmaSale.query.filter_by(commercial_id=current_user.id).all()
        return render_template('mes_ventes.html', ventes_nova=ventes_nova, ventes_ramopharma=ventes_ramopharma)

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
        func.sum(farmalfaSale.quantity * farmalfaSale.price) + func.sum(opalaSale.quantity * opalaSale.price)
    ).filter(
        or_(
            farmalfaSale.project == 'nasmedic',
            opalaSale.project == 'nasmedic'
        )
    ).scalar() or 0
    
    total_visits = len(prospections)
    
    # Récupérer le chiffre d'affaire mensuel pour NASMEDIC
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', farmalfaSale.date).label('month'),
        func.sum(farmalfaSale.quantity * farmalfaSale.price).label('farmalfa_favre_revenue'),
        func.sum(opalaSale.quantity * opalaSale.price).label('trois_chene_revenue')
    ).outerjoin(opalaSale, func.strftime('%Y-%m', opalaSale.date) == func.strftime('%Y-%m', farmalfaSale.date)) \
     .filter(or_(farmalfaSale.project == 'nasmedic', opalaSale.project == 'nasmedic')) \
     .group_by('month').order_by('month').all()
    
    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_farmalfa = [row.farmalfa_favre_revenue or 0 for row in monthly_revenue]
    monthly_revenue_trois = [row.trois_chene_revenue or 0 for row in monthly_revenue]
    monthly_revenue_total = [sum(x) for x in zip(monthly_revenue_farmalfa, monthly_revenue_trois)]
    
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
        monthly_revenue_farmalfa=monthly_revenue_farmalfa,
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
        func.sum(HRASale.quantity * HRASale.price) + func.sum(ramopharmaSale.quantity * ramopharmaSale.price)
    ).filter(
        or_(
            HRASale.project == 'nasderm',
            ramopharmaSale.project == 'nasderm'
        )
    ).scalar() or 0
    
    total_visits = len(prospections)
    
    # Récupérer le chiffre d'affaire mensuel pour NASDERM
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', HRASale.date).label('month'),
        func.sum(HRASale.quantity * HRASale.price).label('nova_pharma_revenue'),
        func.sum(ramopharmaSale.quantity * ramopharmaSale.price).label('ramopharma_revenue')
    ).outerjoin(ramopharmaSale, func.strftime('%Y-%m', ramopharmaSale.date) == func.strftime('%Y-%m', HRASale.date)) \
     .filter(or_(HRASale.project == 'nasderm', ramopharmaSale.project == 'nasderm')) \
     .group_by('month').order_by('month').all()
    
    # Préparer les données pour le graphique
    monthly_revenue_labels = [row.month for row in monthly_revenue]
    monthly_revenue_nova = [row.nova_pharma_revenue or 0 for row in monthly_revenue]
    monthly_revenue_ramopharma = [row.ramopharma_revenue or 0 for row in monthly_revenue]
    monthly_revenue_total = [sum(x) for x in zip(monthly_revenue_nova, monthly_revenue_ramopharma)]
    
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
        monthly_revenue_ramopharma=monthly_revenue_ramopharma,
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
    form.product_id.choices = [(p.id, p.name) for p in HRAProduct.query.all()]

    if form.validate_on_submit():
        product = HRAProduct.query.get(form.product_id.data)
        quantity = form.quantity.data
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = HRASale(
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

    form = AddHRAProductForm()

    if form.validate_on_submit():
        name = form.name.data
        price = form.price.data

        product = HRAProduct(
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

@app.route('/admin/ramopharma/sale', methods=['GET', 'POST'])
@login_required
def admin_add_ramopharma_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminramopharmaSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in ramopharmaProduct.query.all()]

    if form.validate_on_submit():
        product = ramopharmaProduct.query.get(form.product_id.data)
        quantity = form.quantity.data
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = ramopharmaSale(
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
        return redirect(url_for('admin_add_ramopharma_sale'))

    return render_template('admin_add_ramopharma_sale.html', form=form)


@app.route('/admin/ramopharma/product/add', methods=['GET', 'POST'])
@login_required
def add_ramopharma_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddramopharmaProductForm()
    if form.validate_on_submit():
        product = ramopharmaProduct(
            name=form.name.data,
            default_price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_ramopharma_product'))

    return render_template('add_ramopharma_product.html', form=form)


@app.route('/admin/farmalfa_favre/sale', methods=['GET', 'POST'])
@login_required
def admin_add_farmalfa_favre_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminfarmalfaSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in farmalfaProduct.query.all()]

    if form.validate_on_submit():
        product = farmalfaProduct.query.get(form.product_id.data)
        quantity = form.quantity.data
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = farmalfaSale(
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
        return redirect(url_for('admin_add_farmalfa_favre_sale'))

    return render_template('admin_add_farmalfa_favre_sale.html', form=form)


@app.route('/admin/farmalfa_favre/product/add', methods=['GET', 'POST'])
@login_required
def add_farmalfa_favre_product():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AddfarmalfaProductForm()
    if form.validate_on_submit():
        product = farmalfaProduct(
            name=form.name.data,
            default_price=form.price.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès", "success")
        return redirect(url_for('add_farmalfa_favre_product'))

    return render_template('add_farmalfa_favre_product.html', form=form)

@app.route('/admin/trois_chene/sale', methods=['GET', 'POST'])
@login_required
def admin_add_trois_chene_sale():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard'))

    form = AdminopalaSaleForm()
    form.product_id.choices = [(p.id, p.name) for p in opalaProduct.query.all()]

    if form.validate_on_submit():
        product = opalaProduct.query.get(form.product_id.data)
        quantity = form.quantity.data
        entrepot = form.entrepot.data
        sale_date = form.sale_date.data

        sale = opalaSale(
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

    form = AddopalaProductForm()
    if form.validate_on_submit():
        product = opalaProduct(
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

@app.route('/farmalfa_favre_sales', methods=['GET', 'POST'])
@login_required
def farmalfa_favre_sales():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = farmalfaProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('farmalfa_favre_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = farmalfaSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasmedic'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes farmalfa enregistrées avec succès', 'success')
        return redirect(url_for('farmalfa_favre_sales'))
    
    return render_template('farmalfa_favre_sales.html', products=products)

@app.route('/trois_chene_sales', methods=['GET', 'POST'])
@login_required
def trois_chene_sales():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = opalaProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('trois_chene_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = opalaSale(
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
    
    products = HRAProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('nova_pharma_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = HRASale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes HRA enregistrées avec succès', 'success')
        return redirect(url_for('nova_pharma_sales'))
    
    return render_template('nova_pharma_sales.html', products=products)

@app.route('/ramopharma_sales', methods=['GET', 'POST'])
@login_required
def ramopharma_sales():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))
    
    products = ramopharmaProduct.query.all()
    
    if request.method == 'POST':
        sale_date = request.form.get('sale_date')
        if not sale_date:
            flash('Veuillez saisir une date.', 'error')
            return redirect(url_for('ramopharma_sales'))
        
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}')
            price = request.form.get(f'price_{product.id}', product.default_price)
            
            if quantity and int(quantity) > 0:
                sale = ramopharmaSale(
                    product_id=product.id,
                    quantity=int(quantity),
                    price=float(price),
                    date=datetime.strptime(sale_date, '%Y-%m-%d'),
                    commercial_id=current_user.id,
                    project='nasderm'
                )
                db.session.add(sale)
        
        db.session.commit()
        flash('Ventes ramopharma enregistrées avec succès', 'success')
        return redirect(url_for('ramopharma_sales'))
    
    return render_template('ramopharma_sales.html', products=products)

@app.route('/monthly_revenue_nasmedic')
@login_required
def monthly_revenue_nasmedic():
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    monthly_revenue_raw = db.session.query(
        func.strftime('%Y-%m', farmalfaSale.date).label('month'),
        func.sum(farmalfaSale.quantity * farmalfaSale.price).label('farmalfa_favre_revenue'),
        func.sum(opalaSale.quantity * opalaSale.price).label('trois_chene_revenue')
    ).outerjoin(
        opalaSale, func.strftime('%Y-%m', opalaSale.date) == func.strftime('%Y-%m', farmalfaSale.date)
    ).filter(
        or_(farmalfaSale.project == 'nasmedic', opalaSale.project == 'nasmedic')
    ).group_by('month').order_by('month').all()

    monthly_revenue = []
    total = 0.0
    for row in monthly_revenue_raw:
        farmalfa = float(row.farmalfa_favre_revenue or 0)
        trois = float(row.trois_chene_revenue or 0)
        total += farmalfa + trois
        monthly_revenue.append({
            'month': row.month,
            'farmalfa_favre': f"{farmalfa:.2f}",
            'trois_chene': f"{trois:.2f}",
            'total': f"{farmalfa + trois:.2f}"
        })

    return render_template('monthly_revenue_nasmedic.html', monthly_revenue=monthly_revenue, total=f"{total:.2f}")


@app.route('/monthly_revenue_nasderm')
@login_required
def monthly_revenue_nasderm():
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    ramopharma_sale_alias = aliased(ramopharmaSale)

    monthly_revenue_raw = db.session.query(
        func.strftime('%Y-%m', HRASale.date).label('month'),
        func.sum(HRASale.quantity * HRASale.price).label('nova_pharma_revenue'),
        func.sum(ramopharma_sale_alias.quantity * ramopharma_sale_alias.price).label('ramopharma_revenue')
    ).outerjoin(
        ramopharma_sale_alias, func.strftime('%Y-%m', ramopharma_sale_alias.date) == func.strftime('%Y-%m', HRASale.date)
    ).filter(
        or_(HRASale.project == 'nasderm', ramopharma_sale_alias.project == 'nasderm')
    ).group_by('month').order_by('month').all()

    monthly_revenue = []
    total = 0.0
    for row in monthly_revenue_raw:
        nova = float(row.nova_pharma_revenue or 0)
        ramopharma = float(row.ramopharma_revenue or 0)
        total += nova + ramopharma
        monthly_revenue.append({
            'month': row.month,
            'nova_pharma': f"{nova:.2f}",
            'ramopharma': f"{ramopharma:.2f}",
            'total': f"{nova + ramopharma:.2f}"
        })

    return render_template('monthly_revenue_nasderm.html', monthly_revenue=monthly_revenue, total=f"{total:.2f}")

@app.route('/monthly_revenue_detail_nasmedic/<month>')
@login_required
def monthly_revenue_detail_nasmedic(month):
    if current_user.project != 'nasmedic' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    farmalfa_favre_sales = db.session.query(
        farmalfaProduct.name,
        func.sum(farmalfaSale.quantity).label('total_quantity'),
        func.sum(farmalfaSale.quantity * farmalfaSale.price).label('total_revenue')
    ).join(farmalfaProduct, farmalfaSale.product_id == farmalfaProduct.id).filter(
        func.strftime('%Y-%m', farmalfaSale.date) == month,
        farmalfaSale.project == 'nasmedic'
    ).group_by(farmalfaProduct.name).all()

    trois_chene_sales = db.session.query(
        opalaProduct.name,
        func.sum(opalaSale.quantity).label('total_quantity'),
        func.sum(opalaSale.quantity * opalaSale.price).label('total_revenue')
    ).join(opalaProduct, opalaSale.product_id == opalaProduct.id).filter(
        func.strftime('%Y-%m', opalaSale.date) == month,
        opalaSale.project == 'nasmedic'
    ).group_by(opalaProduct.name).all()

    return render_template(
        'monthly_revenue_detail_nasmedic.html',
        month=month,
        farmalfa_favre_sales=farmalfa_favre_sales,
        trois_chene_sales=trois_chene_sales
    )


@app.route('/monthly_revenue_detail_nasderm/<month>')
@login_required
def monthly_revenue_detail_nasderm(month):
    if current_user.project != 'nasderm' and current_user.role != 'admin':
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('home'))

    nova_pharma_sales = db.session.query(
        HRAProduct.name,
        func.sum(HRASale.quantity).label('total_quantity'),
        func.sum(HRASale.quantity * HRASale.price).label('total_revenue')
    ).join(HRAProduct, HRASale.product_id == HRAProduct.id).filter(
        func.strftime('%Y-%m', HRASale.date) == month,
        HRASale.project == 'nasderm'
    ).group_by(HRAProduct.name).all()

    ramopharma_sales = db.session.query(
        ramopharmaProduct.name,
        func.sum(ramopharmaSale.quantity).label('total_quantity'),
        func.sum(ramopharmaSale.quantity * ramopharmaSale.price).label('total_revenue')
    ).join(ramopharmaProduct, ramopharmaSale.product_id == ramopharmaProduct.id).filter(
        func.strftime('%Y-%m', ramopharmaSale.date) == month,
        ramopharmaSale.project == 'nasderm'
    ).group_by(ramopharmaProduct.name).all()

    return render_template(
        'monthly_revenue_detail_nasderm.html',
        month=month,
        nova_pharma_sales=nova_pharma_sales,
        ramopharma_sales=ramopharma_sales
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
        
        # Produits HRA
        nova_pharma_products = [
            ("HYFAC GEL NETTOYANT FLC 150ML", 3.5),
            ("HYFAC GEL NETTOYANT TB 300ML", 3.5),
            # ... (liste complète des produits)
        ]
        
        for name, price in nova_pharma_products:
            if not HRAProduct.query.filter_by(name=name).first():
                db.session.add(HRAProduct(
                    name=name,
                    default_price=price
                ))
        
        # Produits ramopharma
        ramopharma_products = [
            ("ELLE TEST BTE DE 1 TEST GROSSESSE", 3.5),
            ("MOUSTIDOSE SPRAY REPULSIF ZONE INFESTEES IR3535 +12M  100ML", 3.5),
            # ... (liste complète des produits)
        ]
        
        for name, price in ramopharma_products:
            if not ramopharmaProduct.query.filter_by(name=name).first():
                db.session.add(ramopharmaProduct(
                    name=name,
                    default_price=price
                ))
        
        # Produits farmalfa
        farmalfa_favre_products = [
            ("Chronoerect", 3.58),
            ("Special Kid calcium", 2.65),
            # ... (liste complète des produits)
        ]
        
        for name, price in farmalfa_favre_products:
            if not farmalfaProduct.query.filter_by(name=name).first():
                db.session.add(farmalfaProduct(
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
            if not opalaProduct.query.filter_by(name=name).first():
                db.session.add(opalaProduct(
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
