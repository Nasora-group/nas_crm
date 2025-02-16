from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    zone = db.Column(db.String(100), nullable=True)
    project = db.Column(db.String(50), nullable=False)  # 'nasderm' or 'nasmedic'

class Prospection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    nom_client = db.Column(db.String(100), nullable=False)
    specialite = db.Column(db.String(100), nullable=False)
    structure = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(15), nullable=False)
    profils_prospect = db.Column(db.String(200), nullable=True)
    produits_presentés = db.Column(db.String(200), nullable=True)
    produits_prescrits = db.Column(db.String(200), nullable=True)

    commercial = db.relationship('User', backref='prospections')
    
class Planning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # Date de début de la semaine

    # Champs pour chaque jour (matin et soir)
    lundi_matin = db.Column(db.String(200), nullable=True)
    lundi_soir = db.Column(db.String(200), nullable=True)
    mardi_matin = db.Column(db.String(200), nullable=True)
    mardi_soir = db.Column(db.String(200), nullable=True)
    mercredi_matin = db.Column(db.String(200), nullable=True)
    mercredi_soir = db.Column(db.String(200), nullable=True)
    jeudi_matin = db.Column(db.String(200), nullable=True)
    jeudi_soir = db.Column(db.String(200), nullable=True)
    vendredi_matin = db.Column(db.String(200), nullable=True)
    vendredi_soir = db.Column(db.String(200), nullable=True)
    samedi_matin = db.Column(db.String(200), nullable=True)
    samedi_soir = db.Column(db.String(200), nullable=True)
    dimanche_matin = db.Column(db.String(200), nullable=True)
    dimanche_soir = db.Column(db.String(200), nullable=True)

    commercial = db.relationship('User', backref='plannings')

class TroisCheneProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

# Produits Nova Pharma
class NovaPharmaProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

# Produits Gilbert
class GilbertProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

# Produits Eric Favre
class EricFavreProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)


class EricFavreSale(db.Model):
    __tablename__ = 'eric_favre_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('eric_favre_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')  # Ajoutez ce champ
    
class TroisCheneSale(db.Model):
    __tablename__ = 'trois_chene_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('trois_chene_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')  # Ajoutez ce champ

class NovaPharmaSale(db.Model):
    __tablename__ = 'nova_pharma_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('nova_pharma_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')  # Ajoutez ce champ

class GilbertSale(db.Model):
    __tablename__ = 'gilbert_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('gilbert_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')  # Ajoutez ce champ
