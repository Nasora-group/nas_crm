from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SubmitField, PasswordField, SelectField, IntegerField, FloatField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo
from datetime import date
from wtforms.fields import DateField
from wtforms.widgets import TextArea


class DownloadExcelForm(FlaskForm):
    submit = SubmitField('Exporter en Excel')

class AdminSaleForm(FlaskForm):
    product_id = SelectField("Produit", coerce=int, validators=[DataRequired()])
    entrepot = SelectField("Entrepôt", choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField("Quantité", validators=[DataRequired(), NumberRange(min=1)])
    sale_date = DateField("Date de vente", validators=[DataRequired()], default=date.today)
    submit = SubmitField("Valider la vente")

class SalesTargetForm(FlaskForm):
    month = SelectField('Mois', choices=[
        (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
        (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
        (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')
    ], coerce=int, validators=[DataRequired()])
    year = IntegerField('Année', validators=[DataRequired(), NumberRange(min=2020, max=2100)])
    target_amount = FloatField('Objectif (€)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Enregistrer')

class AdminRamopharmaSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    sale_date = DateField("Date de vente", validators=[DataRequired()], default=date.today)
    submit = SubmitField('Enregistrer')

class AdminfarmalfaSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    sale_date = DateField("Date de vente", validators=[DataRequired()], default=date.today)
    submit = SubmitField('Enregistrer')

class AdminOpalaSaleForm(FlaskForm):
    product_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    entrepot = SelectField('Entrepôt', choices=[
        ('DUOPHARM', 'DUOPHARM'),
        ('LABOREX', 'LABOREX'),
        ('UBIPHARM', 'UBIPHARM'),
        ('SODIPHARM', 'SODIPHARM')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    sale_date = DateField("Date de vente", validators=[DataRequired()], default=date.today)
    submit = SubmitField('Enregistrer')

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

    STRUCTURES = [
        ('PHARMACIE', 'PHARMACIE'),
        ('HOPITAL', 'HOPITAL'),
        ('POSTE DE SANTE', 'POSTE DE SANTE'),
        ('CENTRE DE SANTE', 'CENTRE DE SANTE'),
        ('CLINIQUE', 'CLINIQUE'),
        ('SAPEUR POMPIER', 'SAPEUR POMPIER'),
        ('GENDARMERIE', 'GENDARMERIE')
    ]

    # Champs de sélection des structures
    lundi_matin = SelectMultipleField('Lundi Matin', choices=STRUCTURES)
    lundi_matin_details = TextAreaField('Détails Lundi Matin (Nom des structures)')

    lundi_soir = SelectMultipleField('Lundi Soir', choices=STRUCTURES)
    lundi_soir_details = TextAreaField('Détails Lundi Soir')

    mardi_matin = SelectMultipleField('Mardi Matin', choices=STRUCTURES)
    mardi_matin_details = TextAreaField('Détails Mardi Matin')

    mardi_soir = SelectMultipleField('Mardi Soir', choices=STRUCTURES)
    mardi_soir_details = TextAreaField('Détails Mardi Soir')

    mercredi_matin = SelectMultipleField('Mercredi Matin', choices=STRUCTURES)
    mercredi_matin_details = TextAreaField('Détails Mercredi Matin')

    mercredi_soir = SelectMultipleField('Mercredi Soir', choices=STRUCTURES)
    mercredi_soir_details = TextAreaField('Détails Mercredi Soir')

    jeudi_matin = SelectMultipleField('Jeudi Matin', choices=STRUCTURES)
    jeudi_matin_details = TextAreaField('Détails Jeudi Matin')

    jeudi_soir = SelectMultipleField('Jeudi Soir', choices=STRUCTURES)
    jeudi_soir_details = TextAreaField('Détails Jeudi Soir')

    vendredi_matin = SelectMultipleField('Vendredi Matin', choices=STRUCTURES)
    vendredi_matin_details = TextAreaField('Détails Vendredi Matin')

    vendredi_soir = SelectMultipleField('Vendredi Soir', choices=STRUCTURES)
    vendredi_soir_details = TextAreaField('Détails Vendredi Soir')

    samedi_matin = SelectMultipleField('Samedi Matin', choices=STRUCTURES)
    samedi_matin_details = TextAreaField('Détails Samedi Matin')

    samedi_soir = SelectMultipleField('Samedi Soir', choices=STRUCTURES)
    samedi_soir_details = TextAreaField('Détails Samedi Soir')

    dimanche_matin = SelectMultipleField('Dimanche Matin', choices=STRUCTURES)
    dimanche_matin_details = TextAreaField('Détails Dimanche Matin')

    dimanche_soir = SelectMultipleField('Dimanche Soir', choices=STRUCTURES)
    dimanche_soir_details = TextAreaField('Détails Dimanche Soir')

    submit = SubmitField('Valider le planning')


class ProductSaleForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Enregistrer les ventes')

class HRASalesForm(ProductSaleForm):
    pass

class RamopharmaSalesForm(ProductSaleForm):
    pass

class farmalfaSalesForm(ProductSaleForm):
    pass

class OpalaSalesForm(ProductSaleForm):
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
    
class AddHRAProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddRamopharmaProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddfarmalfaProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")

class AddOpalaProductForm(FlaskForm):
    name = StringField("Nom du produit", validators=[DataRequired()])
    price = FloatField("Prix par défaut (€)", validators=[DataRequired()])
    submit = SubmitField("Ajouter")
