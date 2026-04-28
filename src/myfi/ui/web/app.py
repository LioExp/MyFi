from flask import Flask, jsonify, render_template
from myfi.core.config_manager import ConfigManager
from myfi.core.scanner import Scanner
from myfi.db.database import Database
from datetime import date, datetime, timedelta

app = Flask(__name__, template_folder='templates', static_folder='static')

# ----- Rotas de páginas -----
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/automacao')
def automacao():
    return render_template('automacao.html')

@app.route('/dispositivos')
def dispositivos():
    return render_template('dispositivos.html')

@app.route('/alertas')
def alertas():
    return render_template('alertas.html')

@app.route('/ia')
def ia():
    return render_template('dashboard.html')  # placeholder

@app.route('/configuracoes')
def config():
    return render_template('configuracoes.html')

# ----- APIs de dados -----
@app.route('/api/devices')
def api_devices():
    config = ConfigManager()
    scanner = Scanner(config)
    try:
        devices = scanner.scan()
        scanner.save_to_db(devices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Adicionar consumo de hoje a cada dispositivo
    db = Database()
    today = str(date.today())
    for d in devices:
        summary = db.get_traffic_summary(d['mac'], since=today + " 00:00:00")
        total = summary['bytes_sent'] + summary['bytes_recv']
        d['consumo_bytes'] = total
        d['consumo'] = _format_bytes(total)
    db.close()
    return jsonify(devices)

@app.route('/api/dashboard')
def api_dashboard():
    db = Database()
    today = str(date.today())

    devices = db.get_all_devices()
    active_count = len(devices)

    traffic = db.get_traffic_summary(None, since=today + " 00:00:00")
    total_bytes = traffic['bytes_sent'] + traffic['bytes_recv']

    alerts = db.get_alerts(limit=100)
    pending_alerts = [a for a in alerts if a['timestamp'].startswith(today)]
    pending_count = len(pending_alerts)

    # Dados reais do gráfico (últimas 24 horas)
    chart_data = _get_chart_data(db)

    db.close()

    return jsonify({
        'active_devices': active_count,
        'total_devices': active_count,
        'today_traffic_bytes': total_bytes,
        'pending_alerts': pending_count,
        'devices': devices,
        'chart_data': chart_data
    })

@app.route('/api/alerts')
def api_alerts():
    db = Database()
    alerts = db.get_alerts(limit=100)
    # Mapear alert_type para severidade usada no frontend
    for a in alerts:
        if a['alert_type'] in ('critical', 'error'):
            a['severity'] = 'critical'
        elif a['alert_type'] == 'warning':
            a['severity'] = 'warning'
        else:
            a['severity'] = 'info'
    db.close()
    return jsonify(alerts)

# ----- Helpers -----
def _format_bytes(num_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} TB"

def _get_chart_data(db):
    """Retorna lista de {'time': 'HH:MM', 'value': MB} das últimas 24 horas."""
    now = datetime.now()
    start = now - timedelta(hours=24)
    db.cursor.execute('''
        SELECT timestamp, bytes_sent + bytes_recv as total
        FROM traffic_logs
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    ''', (start.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')))
    rows = db.cursor.fetchall()
    hourly = {}
    for row in rows:
        try:
            ts = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            hour_key = ts.replace(minute=0, second=0, microsecond=0)
            hourly[hour_key] = hourly.get(hour_key, 0) + row[1]
        except:
            continue
    result = []
    for i in range(23, -1, -1):
        t = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
        total = hourly.get(t, 0)
        result.append({
            'time': t.strftime('%H:%M'),
            'value': round(total / (1024 * 1024), 2)  # MB
        })
    return result

if __name__ == '__main__':
    app.run(debug=False)