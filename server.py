# server.py
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biogas_data.db'
db = SQLAlchemy(app)

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    methane = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    heat_status = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# API Endpoints
@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.json
    new_entry = SensorData(
        methane=data['methane'],
        temperature=data['temperature'],
        ph=data['ph'],
        heat_status=data['heat_status'],
        timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
    )
    db.session.add(new_entry)
    db.session.commit()
    return jsonify({"message": "Data stored successfully"}), 201

@app.route('/api/latest', methods=['GET'])
def get_latest():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    return jsonify({
        "methane": data.methane,
        "temperature": data.temperature,
        "ph": data.ph,
        "heat_status": data.heat_status,
        "timestamp": data.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    hours = int(request.args.get('hours', 24))
    time_threshold = datetime.utcnow() - timedelta(hours=hours)
    data = SensorData.query.filter(SensorData.timestamp >= time_threshold).all()
    
    return jsonify([{
        "timestamp": d.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "methane": d.methane,
        "temperature": d.temperature,
        "ph": d.ph
    } for d in data])

# Serve dashboard
@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'biogas_dashboard.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
