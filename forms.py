from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SubmitField, PasswordField, SelectField, IntegerField, FloatField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo
from datetime import date
from wtforms.fields import DateField
from wtforms.widgets import TextArea

class AdminSaleForm(FlaskForm):
    product_id = SelectField("Produit", coerce=int, validators=[DataRequired()])
    entrepot = SelectField("Entrepôt", choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField("Quantité", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Valider la vente")


class AdminProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter le produit")


class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class ProspectionForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    nom_client = StringField('Nom du client', validators=[DataRequired(), Length(max=100)])
    specialite = StringField('Spécialité', validators=[DataRequired(), Length(max=100)])
    structure = StringField('Structure', validators=[DataRequired(), Length(max=100)])
    telephone = StringField('Téléphone', validators=[DataRequired(), Length(max=15)])
    profils_prospect = TextAreaField('Profils prospect', widget=TextArea(), validators=[Length(max=200)])
    produits_presentes = TextAreaField('Produits présentés', widget=TextArea(), validators=[Length(max=200)])
    produits_prescrits = TextAreaField('Produits prescrits', widget=TextArea(), validators=[Length(max=200)])
    submit = SubmitField('Enregistrer')

class PlanningForm(FlaskForm):
    date = DateField('Date de début de la semaine', validators=[DataRequired()], default=date.today)

    # Liste des choix pour les structures
    STRUCTURES = [
        ('HOPITAL', 'HOPITAL'),
        ('POSTE DE SANTE', 'POSTE DE SANTE'),
        ('CENTRE DE SANTE', 'CENTRE DE SANTE'),
        ('CLINIQUE', 'CLINIQUE'),
        ('SAPEUR POMPIER', 'SAPEUR POMPIER'),
        ('GENDARMERIE', 'GENDARMERIE')
    ]

    # Champs pour chaque jour (matin et soir)
    lundi_matin = SelectMultipleField('Lundi Matin', choices=STRUCTURES)
    lundi_soir = SelectMultipleField('Lundi Soir', choices=STRUCTURES)
    mardi_matin = SelectMultipleField('Mardi Matin', choices=STRUCTURES)
    mardi_soir = SelectMultipleField('Mardi Soir', choices=STRUCTURES)
    mercredi_matin = SelectMultipleField('Mercredi Matin', choices=STRUCTURES)
    mercredi_soir = SelectMultipleField('Mercredi Soir', choices=STRUCTURES)
    jeudi_matin = SelectMultipleField('Jeudi Matin', choices=STRUCTURES)
    jeudi_soir = SelectMultipleField('Jeudi Soir', choices=STRUCTURES)
    vendredi_matin = SelectMultipleField('Vendredi Matin', choices=STRUCTURES)
    vendredi_soir = SelectMultipleField('Vendredi Soir', choices=STRUCTURES)
    samedi_matin = SelectMultipleField('Samedi Matin', choices=STRUCTURES)
    samedi_soir = SelectMultipleField('Samedi Soir', choices=STRUCTURES)
    dimanche_matin = SelectMultipleField('Dimanche Matin', choices=STRUCTURES)
    dimanche_soir = SelectMultipleField('Dimanche Soir', choices=STRUCTURES)

    submit = SubmitField('Valider le planning')

class ProductSaleForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Enregistrer les ventes')

class NovaPharmaSalesForm(ProductSaleForm):
    pass

class GilbertSalesForm(ProductSaleForm):
    pass

class EricFavreSalesForm(ProductSaleForm):
    pass

class TroisCheneSalesForm(ProductSaleForm):
    pass

class DownloadExcelForm(FlaskForm):
    submit = SubmitField('Télécharger en Excel')

class UserForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(max=150)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Rôle', choices=[('admin', 'Administrateur'), ('commercial', 'Commercial')], validators=[DataRequired()])
    zone = StringField('Zone', validators=[Length(max=100)])
    project = SelectField('Projet', choices=[('nasderm', 'NASDERM'), ('nasmedic', 'NASMEDIC')], validators=[DataRequired()])
    submit = SubmitField('Enregistrer')
    
class AddNovaPharmaProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddGilbertProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddEricFavreProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddTroisCheneProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AdminGilbertSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Enregistrer')


class AdminEricFavreSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Enregistrer')


class AdminTroisCheneSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Enregistrer')
