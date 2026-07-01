# Customer Reviews Sentiment Dashboard

This project has two parts:

- `backend` - a Python service that cleans the review data, trains the sentiment model, and serves product feedback summaries.
- `frontend` - a React + Vite dashboard that lets a user search for a product and view the live ML results.

## Clone the repository

```powershell
git clone <your-repo-url>
cd CUSTMER
```

## Create environment files

Copy the sample env files and update them if you need custom values:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
Copy-Item .\frontend\.env.example .\frontend\.env
```

The backend reads these values:

- `BACKEND_HOST` - host address for the Python server
- `BACKEND_PORT` - port for the Python server

The frontend reads:

- `VITE_API_URL` - backend base URL used by the React app

If you do not want to customize anything, you can still create the `.env` files and keep the default values.

## Install backend libraries

Create a Python virtual environment at the repository root, activate it, then install the backend requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\backend\requirements.txt
```

## Install frontend libraries

```powershell
Set-Location .\frontend
npm i
```

## Run the backend server

From the repository root:

```powershell
Set-Location .\backend
..\.venv\Scripts\python.exe app.py
```

The backend runs on `http://127.0.0.1:8000` by default.

## Run the frontend server

From the `frontend` folder:

```powershell
Set-Location .\frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## How the app works

1. The Python backend reads `backend/data/customer_reviews.csv`.
2. The notebook logic cleans the data, trains the text classifier, and exposes feedback summaries for a selected product.
3. The React frontend sends the product name to the backend and renders the average rating, sentiment split, category mix, and sample reviews.

## Notes

- The project currently uses Positive and Negative sentiment labels.
- The frontend will use the backend proxy in development, or `VITE_API_URL` if you set it in the env file.
- If you change the backend port, update `VITE_API_URL` to match.
