# AI Workshop

Camera scripts + FPL Advisor app (React + Flask).

## Kom igång på en ny dator

### Krav
- **Python 3.10+**
- **Node.js 18+**
- **Git**

### 1. Klona repot
```bash
git clone https://github.com/oscarkav/AI_Workshop.git
cd AI_Workshop
```

### 2. Installera backend (Python)
```bash
cd fpl_app/backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install flask requests
```

### 3. Installera frontend (Node.js)
```bash
cd ../frontend
npm install
```

### 4. Kör appen

**Terminal 1 — Backend:**
```bash
cd fpl_app/backend
.venv\Scripts\activate
python app.py
```

**Terminal 2 — Frontend:**
```bash
cd fpl_app/frontend
npm run dev
```

Appen körs sedan på **http://localhost:5173**.

## Utveckla & pusha ändringar
```bash
git add -A
git commit -m "Din beskrivning av ändringen"
git push
```
