# TATA Stocks - Investment Platform

A Flask-based web application for investing in TATA company stocks with daily returns and referral system.

## Features

- User authentication with Aadhaar verification
- Stock investment with daily returns
- Wallet system for deposits and withdrawals
- Referral system with bonus rewards
- Support ticket system
- Mobile-responsive design

## Tech Stack

- Backend: Python Flask
- Database: Supabase (PostgreSQL)
- Frontend: HTML, CSS, JavaScript
- Authentication: Flask-Login
- Deployment: Render

## Prerequisites

- Python 3.8 or higher
- Supabase account
- Render account (for deployment)

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tatastocks.git
cd tatastocks
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SECRET_KEY=your_flask_secret_key
```

5. Set up the Supabase database:
   - Create a new project in Supabase
   - Run the SQL commands from `schema.sql` in the Supabase SQL editor
   - Enable Row Level Security (RLS) for all tables
   - Set up the required policies

6. Run the application locally:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variables:
     - `SUPABASE_URL`
     - `SUPABASE_KEY`
     - `SECRET_KEY`

## Project Structure

```
tatastocks/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── schema.sql         # Database schema
├── .env              # Environment variables
├── templates/        # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── deposit.html
│   ├── withdraw.html
│   ├── transactions.html
│   ├── investments.html
│   ├── claim.html
│   ├── rules.html
│   ├── referral.html
│   └── support.html
└── static/          # Static files (CSS, JS, images)
```

## Security Features

- Password hashing
- CSRF protection
- Session management
- Row Level Security in database
- Input validation
- Secure headers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@tatastocks.com or create a support ticket in the application. 
 