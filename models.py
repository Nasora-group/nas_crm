# models.py
from extensions import db  # On importe db depuis extensions.py

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... (le reste de tes modèles)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' ou 'commercial'
    zone = db.Column(db.String(100), nullable=True)
    project = db.Column(db.String(50), nullable=False)  # 'nasderm' ou 'nasmedic'

    def __repr__(self):
        return f'<User {self.username}>'

class Prospection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    nom_client = db.Column(db.String(100), nullable=False)
    specialite = db.Column(db.String(100), nullable=False)
    structure = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(15), nullable=False)
    profils_prospect = db.Column(db.String(200), nullable=True)
    produits_presentes = db.Column(db.String(200), nullable=True)
    produits_prescrits = db.Column(db.String(200), nullable=True)

    commercial = db.relationship('User', backref='prospections')
    
    def __repr__(self):
        return f'<Prospection {self.nom_client} - {self.date}>'

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
    
    def __repr__(self):
        return f'<Planning {self.commercial.username} - {self.date}>'

class NovaPharmaProduct(db.Model):
    __tablename__ = 'nova_pharma_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<NovaPharmaProduct {self.name}>'

class GilbertProduct(db.Model):
    __tablename__ = 'gilbert_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<GilbertProduct {self.name}>'

class EricFavreProduct(db.Model):
    __tablename__ = 'eric_favre_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<EricFavreProduct {self.name}>'

class TroisCheneProduct(db.Model):
    __tablename__ = 'trois_chene_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(db.Float, nullable=False)
    stock_duopharm = db.Column(db.Integer, default=0, nullable=False)
    stock_ubipharm = db.Column(db.Integer, default=0, nullable=False)
    stock_laborex = db.Column(db.Integer, default=0, nullable=False)
    stock_sodipharm = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<TroisCheneProduct {self.name}>'

class NovaPharmaSale(db.Model):
    __tablename__ = 'nova_pharma_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('nova_pharma_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')

    product = db.relationship('NovaPharmaProduct', backref='sales')
    commercial = db.relationship('User', backref='nova_pharma_sales')

    def __repr__(self):
        return f'<NovaPharmaSale {self.date} - {self.quantity}x>'

class GilbertSale(db.Model):
    __tablename__ = 'gilbert_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('gilbert_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')

    product = db.relationship('GilbertProduct', backref='sales')
    commercial = db.relationship('User', backref='gilbert_sales')

    def __repr__(self):
        return f'<GilbertSale {self.date} - {self.quantity}x>'

class EricFavreSale(db.Model):
    __tablename__ = 'eric_favre_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('eric_favre_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')

    product = db.relationship('EricFavreProduct', backref='sales')
    commercial = db.relationship('User', backref='eric_favre_sales')

    def __repr__(self):
        return f'<EricFavreSale {self.date} - {self.quantity}x>'

class TroisCheneSale(db.Model):
    __tablename__ = 'trois_chene_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('trois_chene_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')

    product = db.relationship('TroisCheneProduct', backref='sales')
    commercial = db.relationship('User', backref='trois_chene_sales')

    def __repr__(self):
        return f'<TroisCheneSale {self.date} - {self.quantity}x>'