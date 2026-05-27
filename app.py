from datetime import datetime
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-me'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/av_inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(50), nullable=False)
    room_name = db.Column(db.String(120), nullable=False)
    building = db.Column(db.String(120))
    floor = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    devices = db.relationship('Device', backref='room', cascade='all, delete-orphan')


class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    device_name = db.Column(db.String(120), nullable=False)
    device_type = db.Column(db.String(120), nullable=False)
    asset_tag = db.Column(db.String(120))
    serial_number = db.Column(db.String(120))
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    statuses = db.relationship('DeviceStatus', backref='device', cascade='all, delete-orphan')


class DeviceStatus(db.Model):
    __tablename__ = 'device_status'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Functional')
    issue_notes = db.Column(db.Text)
    validated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@app.route('/')
def index():
    rooms = Room.query.filter_by(active=True).order_by(Room.room_number).all()
    selected_room_id = request.args.get('room_id', type=int)
    if not selected_room_id and rooms:
        selected_room_id = rooms[0].id

    selected_room = Room.query.get(selected_room_id) if selected_room_id else None
    room_payload = None
    if selected_room:
        room_payload = _room_with_latest_status(selected_room)

    return render_template('index.html', rooms=rooms, selected_room=selected_room, room_payload=room_payload)


@app.route('/save-validation/<int:room_id>', methods=['POST'])
def save_validation(room_id):
    room = Room.query.get_or_404(room_id)
    for device in room.devices:
        status_value = request.form.get(f'status_{device.id}', 'Functional')
        notes_value = request.form.get(f'notes_{device.id}', '').strip()
        if status_value == 'Not Functional' and not notes_value:
            flash(f'Notes are required when {device.device_name} is marked Not Functional.', 'error')
            return redirect(url_for('index', room_id=room_id))
        record = DeviceStatus(device_id=device.id, status=status_value, issue_notes=notes_value)
        db.session.add(record)
    db.session.commit()
    flash(f'Validation saved for Room {room.room_number}.', 'success')
    return redirect(url_for('index', room_id=room_id))


@app.route('/report')
def report():
    date_param = request.args.get('date', '').strip()
    selected_date = None
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('report'))

    rooms = Room.query.filter_by(active=True).order_by(Room.room_number).all()
    fully_functional = []
    with_issues = []
    unchecked_rooms = []

    for room in rooms:
        payload = _room_with_latest_status(room, selected_date=selected_date)
        if not payload['devices']:
            continue

        checked_devices = [d for d in payload['devices'] if d['validated_at']]
        if len(checked_devices) < len(payload['devices']):
            unchecked_rooms.append(payload)
            continue

        issues = [d for d in payload['devices'] if d['status'] == 'Not Functional']
        if issues:
            with_issues.append({'room': payload, 'issues': issues})
        else:
            fully_functional.append(payload)

    total_rooms = len(rooms)
    rooms_with_issues_count = len(with_issues)
    fully_count = len(fully_functional)
    unchecked_count = len(unchecked_rooms)
    devices_with_issues = sum(len(item['issues']) for item in with_issues)

    return render_template(
        'report.html',
        fully_functional=fully_functional,
        with_issues=with_issues,
        unchecked_rooms=unchecked_rooms,
        selected_date=(selected_date.isoformat() if selected_date else ''),
        summary={
            'total_rooms': total_rooms,
            'fully_count': fully_count,
            'rooms_with_issues': rooms_with_issues_count,
            'unchecked_rooms': unchecked_count,
            'devices_with_issues': devices_with_issues,
        },
    )


@app.route('/report.csv')
def report_csv():
    rows = []
    date_param = request.args.get('date', '').strip()
    selected_date = None
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None

    rooms = Room.query.filter_by(active=True).all()
    for room in rooms:
        payload = _room_with_latest_status(room, selected_date=selected_date)
        for device in payload['devices']:
            if device['status'] == 'Not Functional':
                rows.append([
                    payload['display_name'],
                    device['device_name'],
                    device['device_type'],
                    device['status'],
                    device['issue_notes'] or '',
                    payload['last_validation'] or 'Never',
                ])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Room', 'Device', 'Type', 'Status', 'Issue Notes', 'Last Validation'])
    writer.writerows(rows)
    mem = io.BytesIO(output.getvalue().encode('utf-8'))
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='rooms_with_issues.csv')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_room':
            room = Room(
                room_number=request.form['room_number'],
                room_name=request.form['room_name'],
                building=request.form.get('building'),
                floor=request.form.get('floor'),
                active=True,
            )
            db.session.add(room)
            db.session.commit()
            flash('Room added.', 'success')
        elif action == 'edit_room':
            room = Room.query.get_or_404(request.form.get('room_id', type=int))
            room.room_number = request.form['room_number']
            room.room_name = request.form['room_name']
            room.building = request.form.get('building')
            room.floor = request.form.get('floor')
            db.session.commit()
            flash('Room updated.', 'success')
        elif action == 'delete_room':
            room = Room.query.get_or_404(request.form.get('room_id', type=int))
            db.session.delete(room)
            db.session.commit()
            flash('Room deleted.', 'success')
        elif action == 'add_device':
            device = Device(
                room_id=request.form.get('room_id', type=int),
                device_name=request.form['device_name'],
                device_type=request.form['device_type'],
                asset_tag=request.form.get('asset_tag'),
                serial_number=request.form.get('serial_number'),
                notes=request.form.get('notes'),
                active=True,
            )
            db.session.add(device)
            db.session.commit()
            flash('Device added.', 'success')
        elif action == 'edit_device':
            device = Device.query.get_or_404(request.form.get('device_id', type=int))
            device.room_id = request.form.get('room_id', type=int)
            device.device_name = request.form['device_name']
            device.device_type = request.form['device_type']
            device.asset_tag = request.form.get('asset_tag')
            device.serial_number = request.form.get('serial_number')
            device.notes = request.form.get('notes')
            db.session.commit()
            flash('Device updated.', 'success')
        elif action == 'delete_device':
            device = Device.query.get_or_404(request.form.get('device_id', type=int))
            db.session.delete(device)
            db.session.commit()
            flash('Device deleted.', 'success')
        return redirect(url_for('admin'))

    q = request.args.get('q', '').strip()
    room_query = Room.query
    if q:
        like = f'%{q}%'
        room_query = room_query.filter((Room.room_number.ilike(like)) | (Room.room_name.ilike(like)) | (Room.building.ilike(like)))
    rooms = room_query.order_by(Room.room_number).all()
    devices = Device.query.order_by(Device.room_id, Device.device_name).all()
    return render_template('admin.html', rooms=rooms, devices=devices, q=q)


@app.route('/api/room/<int:room_id>/devices')
def room_devices(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify(_room_with_latest_status(room))


def _room_with_latest_status(room, selected_date=None):
    devices_payload = []
    last_validations = []
    for device in room.devices:
        status_query = DeviceStatus.query.filter_by(device_id=device.id)
        if selected_date:
            status_query = status_query.filter(db.func.date(DeviceStatus.validated_at) == selected_date)

        latest_status = status_query.order_by(DeviceStatus.validated_at.desc()).first()
        status = latest_status.status if latest_status else 'Functional'
        issue_notes = latest_status.issue_notes if latest_status else ''
        validated_at = latest_status.validated_at if latest_status else None
        if validated_at:
            last_validations.append(validated_at)
        devices_payload.append({
            'id': device.id,
            'device_name': device.device_name,
            'device_type': device.device_type,
            'asset_tag': device.asset_tag,
            'serial_number': device.serial_number,
            'status': status,
            'issue_notes': issue_notes,
            'validated_at': validated_at.strftime('%Y-%m-%d %H:%M') if validated_at else None,
        })

    overall_last = max(last_validations).strftime('%Y-%m-%d %H:%M') if last_validations else None
    return {
        'id': room.id,
        'room_number': room.room_number,
        'room_name': room.room_name,
        'building': room.building,
        'floor': room.floor,
        'display_name': f"{room.room_number} - {room.room_name}",
        'last_validation': overall_last,
        'devices': devices_payload,
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
