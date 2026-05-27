# AV Room Inventory Tracker

A lightweight Flask + SQLite web app for AV/IT staff to validate classroom AV devices room-by-room.

## Features
- Room validation workflow (pick room, mark status, add issue notes, save)
- Last validation timestamp per room
- Reports for fully functional rooms and rooms with issues
- CSV export for issue report
- Admin settings for rooms and devices (add/edit/delete)
- Room search in admin page
- One-click "Mark Entire Room Functional"
- Mobile-friendly, simple operations UI

## Pages (MVP)
1. **Room Validation (`/`)**
   - Dropdown to select room
   - Device list with status and issue notes
   - Save validation snapshot
2. **Reports (`/report`)**
   - Summary counts dashboard
   - Fully functional rooms section
   - Rooms with issues section
   - CSV export (`/report.csv`)
3. **Admin (`/admin`)**
   - Manage rooms (add/edit/delete)
   - Manage devices (add/edit/delete)

## Tech Stack
- Backend: Flask + Flask-SQLAlchemy
- Database: SQLite (`/data/av_inventory.db`)
- Frontend: HTML/CSS/JS templates
- Container: Docker + docker-compose

## Run with Docker
### Build
```bash
docker compose build
```

### Start
```bash
docker compose up -d
```

### Access in Browser
- `http://localhost:5000`

## Persistent Data Storage
- SQLite DB stored at `/data/av_inventory.db` inside the container
- Persisted to Docker named volume: `av_inventory_data`

## Database Seed / Reset
### Seed defaults (first run done automatically)
```bash
docker compose exec av-room-inventory-tracker python seed.py
```

### Reset database and reseed
```bash
docker compose down -v
docker compose up -d --build
```

## Local (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python app.py
```

## Seeded Sample Data
- **Room 101**: Projector, Instructor PC, Touch panel, Ceiling speakers, Microphone
- **Room 102**: Display, HDMI input, Camera, Microphone, Control panel

## Basic Page Preview Description
- Navigation header with Room Validation, Reports, and Admin tabs.
- Validation page presents an operational table for quick status marking while walking rooms.
- Report page separates "Fully Functional Rooms" from "Rooms With Issues" and supports CSV export.
- Admin page provides all CRUD operations for rooms and device inventory.
