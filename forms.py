from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SubmitField, PasswordField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length

class DownloadExcelForm(FlaskForm):
    submit = SubmitField('Télécharger en Excel')

class LoginForm(FlaskForm):
    username = StringField('Nom d’utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class ProspectionForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    nom_client = StringField('Nom du client', validators=[DataRequired()])
    specialite = StringField('Spécialité', validators=[DataRequired()])
    structure = StringField('Structure', validators=[DataRequired()])
    telephone = StringField('Téléphone', validators=[DataRequired()])
    profils_prospect = TextAreaField('Profils prospect')
    produits_presentés = TextAreaField('Produits présentés')
    produits_prescrits = TextAreaField('Produits prescrits')
    submit = SubmitField('Enregistrer')
    
from wtforms import SelectMultipleField

class PlanningForm(FlaskForm):
    date = DateField('Date de début de la semaine', validators=[DataRequired()])

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

class NovaPharmaSalesForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()])
    stock_duopharm = IntegerField('Stock DUOPHARM', validators=[DataRequired()])
    stock_ubipharm = IntegerField('Stock UBIPHARM', validators=[DataRequired()])
    stock_laborex = IntegerField('Stock LABOREX', validators=[DataRequired()])
    stock_sodipharm = IntegerField('Stock SODIPHARM', validators=[DataRequired()])
    submit = SubmitField('Enregistrer les ventes')

class GilbertSalesForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()])
    stock_duopharm = IntegerField('Stock DUOPHARM', validators=[DataRequired()])
    stock_ubipharm = IntegerField('Stock UBIPHARM', validators=[DataRequired()])
    stock_laborex = IntegerField('Stock LABOREX', validators=[DataRequired()])
    stock_sodipharm = IntegerField('Stock SODIPHARM', validators=[DataRequired()])
    submit = SubmitField('Enregistrer les ventes')

class EricFavreSalesForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()])
    stock_duopharm = IntegerField('Stock DUOPHARM', validators=[DataRequired()])
    stock_ubipharm = IntegerField('Stock UBIPHARM', validators=[DataRequired()])
    stock_laborex = IntegerField('Stock LABOREX', validators=[DataRequired()])
    stock_sodipharm = IntegerField('Stock SODIPHARM', validators=[DataRequired()])
    submit = SubmitField('Enregistrer les ventes')

class TroisCheneSalesForm(FlaskForm):
    sale_date = DateField('Date de saisie', validators=[DataRequired()])
    stock_duopharm = IntegerField('Stock DUOPHARM', validators=[DataRequired()])
    stock_ubipharm = IntegerField('Stock UBIPHARM', validators=[DataRequired()])
    stock_laborex = IntegerField('Stock LABOREX', validators=[DataRequired()])
    stock_sodipharm = IntegerField('Stock SODIPHARM', validators=[DataRequired()])
    submit = SubmitField('Enregistrer les ventes')