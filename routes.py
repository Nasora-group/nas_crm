from flask import Blueprint, render_template

nasmedic_bp = Blueprint('nasmedic', __name__)
nasderm_bp = Blueprint('nasderm', __name__)

@nasmedic_bp.route('/nasmedic_dashboard')
def nasmedic_dashboard():
    return render_template('nasmedic_dashboard.html')

@nasderm_bp.route('/nasderm_dashboard')
def nasderm_dashboard():
    return render_template('nasderm_dashboard.html')