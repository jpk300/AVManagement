from app import app, db, Room, Device

def seed():
    with app.app_context():
        db.create_all()
        if Room.query.count() > 0:
            print('Database already has data. Skipping seed.')
            return

        r101 = Room(room_number='101', room_name='Lecture Hall A', building='Science Center', floor='1', active=True)
        r102 = Room(room_number='102', room_name='Lecture Hall B', building='Science Center', floor='1', active=True)
        db.session.add_all([r101, r102])
        db.session.flush()

        db.session.add_all([
            Device(room_id=r101.id, device_name='Projector', device_type='Display'),
            Device(room_id=r101.id, device_name='Instructor PC', device_type='Computer'),
            Device(room_id=r101.id, device_name='Touch panel', device_type='Control Interface'),
            Device(room_id=r101.id, device_name='Ceiling speakers', device_type='Audio Output'),
            Device(room_id=r101.id, device_name='Microphone', device_type='Audio Input'),
            Device(room_id=r102.id, device_name='Display', device_type='Display'),
            Device(room_id=r102.id, device_name='HDMI input', device_type='Input'),
            Device(room_id=r102.id, device_name='Camera', device_type='Video Input'),
            Device(room_id=r102.id, device_name='Microphone', device_type='Audio Input'),
            Device(room_id=r102.id, device_name='Control panel', device_type='Control Interface'),
        ])
        db.session.commit()
        print('Seed complete.')

if __name__ == '__main__':
    seed()
