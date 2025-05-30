# models.py
from extensions import db
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import func, extract, Numeric

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' ou 'commercial'
    zone = db.Column(db.String(100), nullable=True)
    project = db.Column(db.String(50), nullable=False)  # 'nasderm' ou 'nasmedic'

    def __repr__(self):
        return f'<User {self.username}>'

    def get_monthly_ca(self, year, month):
        """Retourne le CA mensuel pour ce commercial"""
        if self.project == 'nasmedic':
            eric_ca = db.session.query(
                func.sum(EricFavreSale.quantity * EricFavreSale.price)
            ).filter(
                EricFavreSale.commercial_id == self.id,
                extract('year', EricFavreSale.date) == year,
                extract('month', EricFavreSale.date) == month
            ).scalar() or 0
            
            trois_chene_ca = db.session.query(
                func.sum(TroisCheneSale.quantity * TroisCheneSale.price)
            ).filter(
                TroisCheneSale.commercial_id == self.id,
                extract('year', TroisCheneSale.date) == year,
                extract('month', TroisCheneSale.date) == month
            ).scalar() or 0
            
            return {
                'eric_favre': float(eric_ca),
                'trois_chene': float(trois_chene_ca),
                'total': float(eric_ca + trois_chene_ca)
            }
        else:
            nova_ca = db.session.query(
                func.sum(NovaPharmaSale.quantity * NovaPharmaSale.price)
            ).filter(
                NovaPharmaSale.commercial_id == self.id,
                extract('year', NovaPharmaSale.date) == year,
                extract('month', NovaPharmaSale.date) == month
            ).scalar() or 0
            
            gilbert_ca = db.session.query(
                func.sum(GilbertSale.quantity * GilbertSale.price)
            ).filter(
                GilbertSale.commercial_id == self.id,
                extract('year', GilbertSale.date) == year,
                extract('month', GilbertSale.date) == month
            ).scalar() or 0
            
            return {
                'nova_pharma': float(nova_ca),
                'gilbert': float(gilbert_ca),
                'total': float(nova_ca + gilbert_ca)
            }

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
    
    @classmethod
    def get_monthly_stats(cls, commercial_id, year, month):
        """Retourne les stats mensuelles de prospection"""
        prospections = cls.query.filter(
            cls.commercial_id == commercial_id,
            extract('year', cls.date) == year,
            extract('month', cls.date) == month
        ).all()
        
        produits_presentes = sum(1 for p in prospections if p.produits_presentes)
        produits_prescrits = sum(1 for p in prospections if p.produits_prescrits)
        
        return {
            'nb_visites': len(prospections),
            'produits_presentes': produits_presentes,
            'produits_prescrits': produits_prescrits,
            'taux_conversion': (produits_prescrits / produits_presentes * 100) if produits_presentes > 0 else 0
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')

class SalesTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    target_amount = db.Column(Numeric(10, 2), nullable=False)
    
    commercial = db.relationship('User', backref='targets')

class Planning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    lundi_matin = db.Column(db.PickleType)
    lundi_matin_details = db.Column(db.Text)

    lundi_soir = db.Column(db.PickleType)
    lundi_soir_details = db.Column(db.Text)

    mardi_matin = db.Column(db.PickleType)
    mardi_matin_details = db.Column(db.Text)

    mardi_soir = db.Column(db.PickleType)
    mardi_soir_details = db.Column(db.Text)

    mercredi_matin = db.Column(db.PickleType)
    mercredi_matin_details = db.Column(db.Text)

    mercredi_soir = db.Column(db.PickleType)
    mercredi_soir_details = db.Column(db.Text)

    jeudi_matin = db.Column(db.PickleType)
    jeudi_matin_details = db.Column(db.Text)

    jeudi_soir = db.Column(db.PickleType)
    jeudi_soir_details = db.Column(db.Text)

    vendredi_matin = db.Column(db.PickleType)
    vendredi_matin_details = db.Column(db.Text)

    vendredi_soir = db.Column(db.PickleType)
    vendredi_soir_details = db.Column(db.Text)

    samedi_matin = db.Column(db.PickleType)
    samedi_matin_details = db.Column(db.Text)

    samedi_soir = db.Column(db.PickleType)
    samedi_soir_details = db.Column(db.Text)

    dimanche_matin = db.Column(db.PickleType)
    dimanche_matin_details = db.Column(db.Text)

    dimanche_soir = db.Column(db.PickleType)
    dimanche_soir_details = db.Column(db.Text)

class NovaPharmaProduct(db.Model):
    __tablename__ = 'nova_pharma_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    default_price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
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
    default_price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
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
    default_price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
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
    default_price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
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
    price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')

    product = db.relationship('NovaPharmaProduct', backref='sales')
    commercial = db.relationship('User', backref='nova_pharma_sales')

    def __repr__(self):
        return f'<NovaPharmaSale {self.date} - {self.quantity}x>'
    
    @property
    def total(self):
        return float(self.quantity * self.price)

class GilbertSale(db.Model):
    __tablename__ = 'gilbert_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('gilbert_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasderm')

    product = db.relationship('GilbertProduct', backref='sales')
    commercial = db.relationship('User', backref='gilbert_sales')

    def __repr__(self):
        return f'<GilbertSale {self.date} - {self.quantity}x>'
    
    @property
    def total(self):
        return float(self.quantity * self.price)

class EricFavreSale(db.Model):
    __tablename__ = 'eric_favre_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('eric_favre_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')

    product = db.relationship('EricFavreProduct', backref='sales')
    commercial = db.relationship('User', backref='eric_favre_sales')

    def __repr__(self):
        return f'<EricFavreSale {self.date} - {self.quantity}x>'
    
    @property
    def total(self):
        return float(self.quantity * self.price)

class TroisCheneSale(db.Model):
    __tablename__ = 'trois_chene_sale'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('trois_chene_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(Numeric(10, 2), nullable=False)  # Modifié ici
    date = db.Column(db.Date, nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.Column(db.String(50), nullable=False, default='nasmedic')

    product = db.relationship('TroisCheneProduct', backref='sales')
    commercial = db.relationship('User', backref='trois_chene_sales')

    def __repr__(self):
        return f'<TroisCheneSale {self.date} - {self.quantity}x>'
    
    @property
    def total(self):
        return float(self.quantity * self.price)