# silkflow

# SilkFlow

A Flask-based web application for managing employee vacation requests, with built-in authentication, logging, and an admin log viewer.

---

## Features

- **User Authentication** — Secure login and session management via `auth.py`
- **Vacation Management** — Submit, view, and manage vacation requests through `vacations.py`
- **Database Integration** — Persistent data storage handled by `database.py`
- **Activity Logging** — Application events and actions are tracked via `logger.py`
- **Log Viewer** — Admin interface to browse logs through `logs_viewer.py`
- **Responsive Frontend** — Built with HTML, CSS, and JavaScript templates

---

## Project Structure

```
silkflow/
├── app.py              # Main Flask application and route definitions
├── auth.py             # Authentication logic (login, logout, session)
├── database.py         # Database models and connection setup
├── logger.py           # Logging configuration and helpers
├── logs_viewer.py      # Routes and logic for the admin log viewer
├── vacations.py        # Vacation request logic and routes
├── test_app.py         # Unit tests
├── requirements.txt    # Python dependencies
├── static/             # CSS, JavaScript, and other static assets
├── templates/          # Jinja2 HTML templates
├── .gitignore
└── LICENSE             # Apache 2.0
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/MarBifrost/silkflow.git
cd silkflow
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the root directory and set the following (adjust as needed):

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///silkflow.db
```

5. **Run the application**

```bash
flask run
```

The app will be available at `http://127.0.0.1:5000`.

---

## Running Tests

```bash
python -m pytest test_app.py
```

---

## Tech Stack

| Layer      | Technology          |
|------------|---------------------|
| Backend    | Python, Flask       |
| Frontend   | HTML,CSS,JavaScript |
| Database   | MySQL               |
| Auth       | Flask sessions      |
| License    | Apache 2.0          |

---

## License

This project is licensed under the [Apache 2.0 License](LICENSE).

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.
