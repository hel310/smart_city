# Neo-Sousse 2030 - Smart City Platform

Welcome to the Neo-Sousse 2030 Smart City Platform! This guide will help you set up the project from scratch.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Python 3.9+**
- **Node.js** (and npm)
- **PostgreSQL** with the **TimescaleDB** extension.

---

## 1. Database Setup

### Install TimescaleDB
You need to install TimescaleDB to handle the time-series data. 
- For Windows/Mac/Linux, follow the official documentation to install: [TimescaleDB Installation Guide](https://docs.timescale.com/install/latest/)
- Alternatively, you can use Docker:
  ```bash
  docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=votre_mot_de_passe timescale/timescaledb-ha:pg15
  ```

### Create the Database
Connect to your PostgreSQL server and create the database:
```sql
CREATE DATABASE smart_city;
```

### Create Tables and Schema
The project uses `schema.sql` located in the `database` folder to create the required tables. Run the following command from the root of the project:
```bash
psql -U postgres -d smart_city -f database/schema.sql
```

### Populate with Seed Data
To insert the initial mock data into your tables, run the `seed_data.sql` script located in the root folder:
```bash
psql -U postgres -d smart_city -f seed_data.sql
```

---

## 2. Environment Variables

Create a `.env` file in the root of the project by copying the provided example file:
```bash
cp .env.example .env
```
Open the `.env` file and update it with your actual database credentials and API keys (such as `GROQ_API_KEY` for the AI module).

---

## 3. Backend Setup (Python / FastAPI)

It is highly recommended to use a virtual environment.

### Install Python Requirements
```bash
# Optional: Create and activate a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt
```

### Update Requirements (If needed)
If you install new packages during development, make sure to update the `requirements.txt` file:
```bash
pip freeze > requirements.txt
```

### Run the Backend
Start the FastAPI backend server using Uvicorn:
```bash
uvicorn backend.main:app --reload
```
The backend will be available at: `http://localhost:8000`

---

## 4. Frontend Setup (React / Vite)

Open a new terminal window to start the frontend.

### Install Node Dependencies
Navigate to the `frontend` folder and install the dependencies:
```bash
cd frontend
npm install
```

### Run the Frontend
Start the Vite development server:
```bash
npm run dev
```
The frontend will typically be accessible at: `http://localhost:5173` (check the terminal output for the exact URL).
