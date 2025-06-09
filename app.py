from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from supabase import create_client
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Initialize admin Supabase client
admin_supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Verify environment variables
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY') or not os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
    raise ValueError("Missing required Supabase environment variables. Please check your .env file.")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

class User(UserMixin):
    def __init__(self, id, name, aadhaar, mobile, wallet_balance=0, is_admin=False):
        self.id = id
        self.name = name
        self.aadhaar = aadhaar
        self.mobile = mobile
        self.wallet_balance = wallet_balance
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = supabase.table('users').select('*').eq('id', user_id).execute()
        if user_data.data:
            user = user_data.data[0]
            return User(
                user['id'],
                user['name'],
                user['aadhaar'],
                user['mobile'],
                user['wallet_balance'],
                user['is_admin']
            )
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        aadhaar = request.form.get('aadhaar')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('index'))

        try:
            # Check if user already exists
            existing_user = supabase.table('users').select('*').eq('mobile', mobile).execute()
            if existing_user.data:
                flash('User already exists!')
                return redirect(url_for('index'))

            # Create new user
            new_user = supabase.table('users').insert({
                'name': name,
                'aadhaar': aadhaar,
                'mobile': mobile,
                'password': password,
                'wallet_balance': 0,
                'is_admin': False
            }).execute()

            if new_user.data:
                user = User(
                    new_user.data[0]['id'],
                    name,
                    aadhaar,
                    mobile,
                    0,
                    False
                )
                login_user(user)
                return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error during registration: {str(e)}')
            return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')

        try:
            user_data = supabase.table('users').select('*').eq('mobile', mobile).eq('password', password).execute()
            if user_data.data:
                user = User(
                    user_data.data[0]['id'],
                    user_data.data[0]['name'],
                    user_data.data[0]['aadhaar'],
                    user_data.data[0]['mobile'],
                    user_data.data[0]['wallet_balance'],
                    user_data.data[0]['is_admin']
                )
                login_user(user)
                # Redirect admin users to admin panel
                if user.is_admin:
                    return redirect(url_for('admin'))
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials!')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error during login: {str(e)}')
            return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        stocks = supabase.table('stocks').select('*').execute()
        return render_template('dashboard.html', stocks=stocks.data)
    except Exception as e:
        flash(f'Error loading stocks: {str(e)}')
        return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        utr_number = request.form.get('utr_number')
        sender_name = request.form.get('sender_name')

        if amount < 500:
            flash('Minimum deposit amount is 500!')
            return redirect(url_for('deposit'))

        try:
            # Create transaction record
            supabase.table('transactions').insert({
                'user_id': current_user.id,
                'type': 'deposit',
                'amount': amount,
                'utr_number': utr_number,
                'sender_name': sender_name,
                'status': 'pending'
            }).execute()
            
            flash('Deposit request submitted successfully!')
            return redirect(url_for('transactions'))
        except Exception as e:
            flash(f'Error during deposit: {str(e)}')
            return redirect(url_for('deposit'))

    return render_template('deposit.html')

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        account_details = request.form.get('account_details')

        if amount < 1000:
            flash('Minimum withdrawal amount is 1000!')
            return redirect(url_for('withdraw'))

        if amount > current_user.wallet_balance:
            flash('Insufficient balance!')
            return redirect(url_for('withdraw'))

        try:
            # Create transaction record
            supabase.table('transactions').insert({
                'user_id': current_user.id,
                'type': 'withdraw',
                'amount': amount,
                'account_details': account_details,
                'status': 'pending'
            }).execute()
            
            flash('Withdrawal request submitted successfully!')
            return redirect(url_for('transactions'))
        except Exception as e:
            flash(f'Error during withdrawal: {str(e)}')
            return redirect(url_for('withdraw'))

    return render_template('withdraw.html')

@app.route('/transactions')
@login_required
def transactions():
    try:
        transactions = supabase.table('transactions').select('*').eq('user_id', current_user.id).order('created_at', desc=True).execute()
        return render_template('transactions.html', transactions=transactions.data)
    except Exception as e:
        flash(f'Error loading transactions: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/investments')
@login_required
def investments():
    try:
        # Get user's investments with stock details
        investments = supabase.table('investments').select('*, stocks(name)').eq('user_id', current_user.id).execute()
        
        # Process investments to add stock name and active status
        processed_investments = []
        current_time = datetime.now(pytz.UTC)  # Get current time in UTC
        
        for investment in investments.data:
            investment['stock_name'] = investment['stocks']['name']
            # Convert end_date to timezone-aware datetime
            end_date = datetime.fromisoformat(investment['end_date'].replace('Z', '+00:00'))
            investment['is_active'] = end_date > current_time
            processed_investments.append(investment)
        
        return render_template('investments.html', investments=processed_investments)
    except Exception as e:
        print(f"Error loading investments: {str(e)}")
        flash(f'Error loading investments: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/claim', methods=['GET', 'POST'])
@login_required
def claim():
    if request.method == 'POST':
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)
        
        # Check if time is between 6 AM and 10 PM
        if not (6 <= current_time.hour < 22):
            flash('Claims are only available between 6 AM and 10 PM IST!')
            return redirect(url_for('claim'))

        try:
            investment_id = request.form.get('investment_id')
            if not investment_id:
                flash('Invalid investment!')
                return redirect(url_for('claim'))

            # Get investment details
            investment = supabase.table('investments').select('*').eq('id', investment_id).eq('user_id', current_user.id).execute()
            if not investment.data:
                flash('Investment not found!')
                return redirect(url_for('claim'))

            investment = investment.data[0]
            
            # Check if already claimed today
            today = datetime.now().date()
            claims = supabase.table('claims').select('*').eq('investment_id', investment_id).eq('date', today.isoformat()).execute()
            
            if claims.data:
                flash('You have already claimed returns for this investment today!')
                return redirect(url_for('claim'))
            
            # Process claim
            supabase.table('claims').insert({
                'investment_id': investment_id,
                'user_id': current_user.id,
                'amount': investment['daily_return'],
                'date': today.isoformat()
            }).execute()
            
            # Get current wallet balance
            user_data = supabase.table('users').select('wallet_balance').eq('id', current_user.id).execute()
            if not user_data.data:
                flash('User data not found!')
                return redirect(url_for('claim'))
            
            current_balance = user_data.data[0]['wallet_balance']
            new_balance = current_balance + investment['daily_return']
            
            # Update wallet balance
            supabase.table('users').update({
                'wallet_balance': new_balance
            }).eq('id', current_user.id).execute()
            
            flash('Daily return claimed successfully!')
            return redirect(url_for('claim'))
        except Exception as e:
            print(f"Error processing claim: {str(e)}")
            flash(f'Error processing claim: {str(e)}')
            return redirect(url_for('claim'))

    try:
        # Get user's investments with stock details
        investments = supabase.table('investments').select('*, stocks(name)').eq('user_id', current_user.id).execute()
        
        # Get today's claims
        today = datetime.now().date()
        claims = supabase.table('claims').select('*').eq('user_id', current_user.id).eq('date', today.isoformat()).execute()
        
        # Create a set of investment IDs that have been claimed today
        claimed_investments = {claim['investment_id'] for claim in claims.data}
        
        # Process investments to add additional information
        processed_investments = []
        current_time = datetime.now(pytz.UTC)
        
        for investment in investments.data:
            # Add stock name
            investment['stock_name'] = investment['stocks']['name']
            
            # Check if investment is active
            end_date = datetime.fromisoformat(investment['end_date'].replace('Z', '+00:00'))
            investment['is_active'] = end_date > current_time
            
            # Calculate remaining days
            investment['remaining_days'] = (end_date - current_time).days
            
            # Check if claimed today
            investment['claimed_today'] = investment['id'] in claimed_investments
            
            if investment['is_active']:
                processed_investments.append(investment)
        
        # Check if user can claim (between 6 AM and 10 PM IST)
        ist = pytz.timezone('Asia/Kolkata')
        current_time_ist = datetime.now(ist)
        can_claim = 6 <= current_time_ist.hour < 22
        
        return render_template('claim.html', 
                             investments=processed_investments,
                             can_claim=can_claim)
    except Exception as e:
        print(f"Error loading investments: {str(e)}")
        flash(f'Error loading investments: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/rules')
@login_required
def rules():
    return render_template('rules.html')

@app.route('/referral', methods=['GET', 'POST'])
@login_required
def referral():
    if request.method == 'POST':
        referred_name = request.form.get('referred_name')
        referred_aadhaar = request.form.get('referred_aadhaar')
        stock_amount = request.form.get('stock_amount')

        try:
            # Create referral request
            new_referral = supabase.table('referrals').insert({
                'referrer_id': current_user.id,
                'referred_name': referred_name,
                'referred_aadhaar': referred_aadhaar,
                'stock_amount': stock_amount,
                'commission': float(stock_amount) * 0.15,  # 15% commission
                'status': 'pending'
            }).execute()

            flash('Referral request submitted successfully!', 'success')
            return redirect(url_for('referral'))

        except Exception as e:
            flash(f'Error submitting referral: {str(e)}', 'error')
            return redirect(url_for('referral'))

    try:
        # Get user's referral requests
        referral_requests = supabase.table('referrals').select('*').eq('referrer_id', current_user.id).order('created_at', desc=True).execute()
        return render_template('referral.html', referral_requests=referral_requests.data)
    except Exception as e:
        flash(f'Error loading referrals: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        query_type = request.form.get('query_type')
        complaint = request.form.get('complaint')

        try:
            # Create support ticket
            new_ticket = supabase.table('support_tickets').insert({
                'user_id': current_user.id,
                'category': query_type,
                'subject': query_type.title(),
                'message': complaint,
                'status': 'open'
            }).execute()

            flash('Support ticket submitted successfully!', 'success')
            return redirect(url_for('support'))

        except Exception as e:
            flash(f'Error submitting ticket: {str(e)}', 'error')
            return redirect(url_for('support'))

    try:
        # Get user's support tickets
        tickets = supabase.table('support_tickets').select('*').eq('user_id', current_user.id).order('created_at', desc=True).execute()
        return render_template('support.html', tickets=tickets.data)
    except Exception as e:
        flash(f'Error loading tickets: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/buy_stock', methods=['POST'])
@login_required
def buy_stock():
    try:
        stock_id = request.form.get('stock_id')
        if not stock_id:
            flash('Stock ID is required!')
            return redirect(url_for('dashboard'))

        # Get stock details
        stock = supabase.table('stocks').select('*').eq('id', stock_id).execute()
        if not stock.data:
            flash('Stock not found!')
            return redirect(url_for('dashboard'))

        stock = stock.data[0]
        
        if current_user.wallet_balance < stock['package']:
            flash('Insufficient balance!')
            return redirect(url_for('dashboard'))

        # Get current wallet balance
        user_data = supabase.table('users').select('wallet_balance').eq('id', current_user.id).execute()
        if not user_data.data:
            flash('User data not found!')
            return redirect(url_for('dashboard'))
        
        current_balance = user_data.data[0]['wallet_balance']
        if current_balance < stock['package']:
            flash('Insufficient balance!')
            return redirect(url_for('dashboard'))

        # Calculate new balance
        new_balance = current_balance - stock['package']

        # Create investment
        investment = supabase.table('investments').insert({
            'user_id': current_user.id,
            'stock_id': stock_id,
            'package': stock['package'],
            'daily_return': stock['daily_return'],
            'total_return': stock['total_return'],
            'tenure_days': stock['tenure_days'],
            'start_date': datetime.now().isoformat(),
            'end_date': (datetime.now() + timedelta(days=stock['tenure_days'])).isoformat()
        }).execute()

        if not investment.data:
            flash('Failed to create investment!')
            return redirect(url_for('dashboard'))

        # Update wallet balance
        result = supabase.table('users').update({
            'wallet_balance': new_balance
        }).eq('id', current_user.id).execute()

        if not result.data:
            flash('Failed to update wallet balance!')
            return redirect(url_for('dashboard'))

        flash('Stock purchased successfully!')
        return redirect(url_for('investments'))
    except Exception as e:
        print(f"Error purchasing stock: {str(e)}")
        flash(f'Error purchasing stock: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin():
    try:
        # Get all users
        users = supabase.table('users').select('*').execute()
        
        # Get all deposits
        deposits = supabase.table('transactions').select('*, users(name)').eq('type', 'deposit').order('created_at', desc=True).execute()
        
        # Get all withdrawals
        withdrawals = supabase.table('transactions').select('*, users(name)').eq('type', 'withdraw').order('created_at', desc=True).execute()
        
        # Get all referrals
        referrals = supabase.table('referrals').select('*, users(name)').order('created_at', desc=True).execute()
        
        return render_template('admin.html',
                             users=users.data,
                             deposits=deposits.data,
                             withdrawals=withdrawals.data,
                             referrals=referrals.data)
    except Exception as e:
        flash(f'Error loading admin data: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/admin/update_wallet', methods=['POST'])
@login_required
@admin_required
def update_wallet():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_balance = data.get('new_balance')
        
        if not user_id or new_balance is None:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Update user's wallet balance
        supabase.table('users').update({
            'wallet_balance': new_balance
        }).eq('id', user_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/approve_transaction', methods=['POST'])
@login_required
@admin_required
def approve_transaction():
    try:
        data = request.get_json()
        transaction_type = data.get('type')
        transaction_id = data.get('transaction_id')
        
        if not transaction_type or not transaction_id:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        if transaction_type == 'referral':
            print(f"Processing referral approval for ID: {transaction_id}")
            
            # Get referral details
            referral = supabase.table('referrals').select('*').eq('id', transaction_id).execute()
            if not referral.data:
                print(f"Referral not found for ID: {transaction_id}")
                return jsonify({'success': False, 'error': 'Referral not found'})
            
            referral = referral.data[0]
            print(f"Found referral: {referral}")
            
            # Check if referral is already processed
            if referral['status'] != 'pending':
                print(f"Referral already processed. Current status: {referral['status']}")
                return jsonify({'success': False, 'error': 'Referral already processed'})
            
            # Get referrer's current wallet balance
            user_data = supabase.table('users').select('wallet_balance').eq('id', referral['referrer_id']).execute()
            if not user_data.data:
                print(f"Referrer not found for ID: {referral['referrer_id']}")
                return jsonify({'success': False, 'error': 'Referrer not found'})
            
            current_balance = user_data.data[0]['wallet_balance']
            print(f"Current wallet balance: {current_balance}")
            
            # Calculate commission (15% of stock amount)
            commission = float(referral['stock_amount']) * 0.15
            print(f"Calculated commission: {commission}")
            
            try:
                # Update referral status using service role key
                print("Attempting to update referral status...")
                try:
                    update_result = admin_supabase.table('referrals').update({
                        'status': 'approved',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', transaction_id).execute()
                    print(f"Update result: {update_result}")
                except Exception as update_error:
                    print(f"Error updating referral status: {str(update_error)}")
                    return jsonify({'success': False, 'error': f'Error updating referral status: {str(update_error)}'})
                
                # Verify the update was successful
                try:
                    updated_referral = admin_supabase.table('referrals').select('status').eq('id', transaction_id).execute()
                    print(f"Verification result: {updated_referral}")
                    if not updated_referral.data:
                        print("No data returned from verification query")
                        return jsonify({'success': False, 'error': 'Failed to verify referral status update'})
                    if updated_referral.data[0]['status'] != 'approved':
                        print(f"Status mismatch. Expected: approved, Got: {updated_referral.data[0]['status']}")
                        return jsonify({'success': False, 'error': 'Failed to update referral status'})
                except Exception as verify_error:
                    print(f"Error verifying referral status: {str(verify_error)}")
                    return jsonify({'success': False, 'error': f'Error verifying referral status: {str(verify_error)}'})
                
                print("Successfully updated referral status")
                
                # Update referrer's wallet balance
                new_balance = current_balance + commission
                print(f"Updating wallet balance to: {new_balance}")
                
                try:
                    wallet_result = admin_supabase.table('users').update({
                        'wallet_balance': new_balance,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', referral['referrer_id']).execute()
                    print(f"Wallet update result: {wallet_result}")
                except Exception as wallet_error:
                    print(f"Error updating wallet balance: {str(wallet_error)}")
                    # Revert referral status
                    admin_supabase.table('referrals').update({
                        'status': 'pending',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', transaction_id).execute()
                    return jsonify({'success': False, 'error': f'Error updating wallet balance: {str(wallet_error)}'})
                
                # Verify the wallet update was successful
                try:
                    updated_user = admin_supabase.table('users').select('wallet_balance').eq('id', referral['referrer_id']).execute()
                    print(f"Wallet verification result: {updated_user}")
                    if not updated_user.data:
                        print("No data returned from wallet verification query")
                        # Revert referral status
                        admin_supabase.table('referrals').update({
                            'status': 'pending',
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', transaction_id).execute()
                        return jsonify({'success': False, 'error': 'Failed to verify wallet balance update'})
                    if abs(updated_user.data[0]['wallet_balance'] - new_balance) > 0.01:
                        print(f"Balance mismatch. Expected: {new_balance}, Got: {updated_user.data[0]['wallet_balance']}")
                        # Revert referral status
                        admin_supabase.table('referrals').update({
                            'status': 'pending',
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', transaction_id).execute()
                        return jsonify({'success': False, 'error': 'Failed to update wallet balance'})
                except Exception as verify_wallet_error:
                    print(f"Error verifying wallet balance: {str(verify_wallet_error)}")
                    # Revert referral status
                    admin_supabase.table('referrals').update({
                        'status': 'pending',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', transaction_id).execute()
                    return jsonify({'success': False, 'error': f'Error verifying wallet balance: {str(verify_wallet_error)}'})
                
                print("Successfully updated wallet balance")
                return jsonify({'success': True})
                
            except Exception as e:
                print(f"Error during referral approval: {str(e)}")
                # Revert referral status if any error occurs
                try:
                    print("Attempting to revert referral status...")
                    admin_supabase.table('referrals').update({
                        'status': 'pending',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', transaction_id).execute()
                except Exception as revert_error:
                    print(f"Error reverting referral status: {str(revert_error)}")
                return jsonify({'success': False, 'error': str(e)})
        else:
            # Get transaction details
            transaction = supabase.table('transactions').select('*').eq('id', transaction_id).execute()
            if not transaction.data:
                return jsonify({'success': False, 'error': 'Transaction not found'})
            
            transaction = transaction.data[0]
            
            # Check if transaction is already processed
            if transaction['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Transaction already processed'})
            
            # Get user's current wallet balance
            user_data = supabase.table('users').select('wallet_balance').eq('id', transaction['user_id']).execute()
            if not user_data.data:
                return jsonify({'success': False, 'error': 'User not found'})
            
            current_balance = user_data.data[0]['wallet_balance']
            
            # For withdrawals, check balance before proceeding
            if transaction_type == 'withdraw' and current_balance < transaction['amount']:
                return jsonify({'success': False, 'error': 'Insufficient balance'})
            
            # Update transaction status
            supabase.table('transactions').update({
                'status': 'approved'
            }).eq('id', transaction_id).execute()
            
            # Verify the update was successful
            updated_transaction = supabase.table('transactions').select('status').eq('id', transaction_id).execute()
            if not updated_transaction.data or updated_transaction.data[0]['status'] != 'approved':
                return jsonify({'success': False, 'error': 'Failed to update transaction status'})
            
            # Update user's wallet balance
            if transaction_type == 'deposit':
                new_balance = current_balance + transaction['amount']
            else:  # withdraw
                new_balance = current_balance - transaction['amount']
            
            # Update wallet balance
            supabase.table('users').update({
                'wallet_balance': new_balance
            }).eq('id', transaction['user_id']).execute()
            
            # Verify the wallet update was successful
            updated_user = supabase.table('users').select('wallet_balance').eq('id', transaction['user_id']).execute()
            if not updated_user.data or abs(updated_user.data[0]['wallet_balance'] - new_balance) > 0.01:
                # Revert transaction status if update fails
                supabase.table('transactions').update({
                    'status': 'rejected'
                }).eq('id', transaction_id).execute()
                return jsonify({'success': False, 'error': 'Failed to update wallet balance'})
            
            return jsonify({'success': True})
    except Exception as e:
        print(f"Error in approve_transaction: {str(e)}")
        # Try to revert transaction status if there's an error
        try:
            if transaction_type == 'referral':
                supabase.table('referrals').update({
                    'status': 'pending'
                }).eq('id', transaction_id).execute()
            else:
                supabase.table('transactions').update({
                    'status': 'rejected'
                }).eq('id', transaction_id).execute()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/reject_transaction', methods=['POST'])
@login_required
@admin_required
def reject_transaction():
    try:
        data = request.get_json()
        transaction_type = data.get('type')
        transaction_id = data.get('transaction_id')
        
        if not transaction_type or not transaction_id:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        if transaction_type == 'referral':
            # Get referral details
            referral = supabase.table('referrals').select('*').eq('id', transaction_id).execute()
            if not referral.data:
                return jsonify({'success': False, 'error': 'Referral not found'})
            
            referral = referral.data[0]
            
            # Check if referral is already processed
            if referral['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Referral already processed'})
            
            # Update referral status
            result = supabase.table('referrals').update({
                'status': 'rejected'
            }).eq('id', transaction_id).execute()
            
            if not result.data:
                return jsonify({'success': False, 'error': 'Failed to update referral status'})
            
            return jsonify({'success': True})
        else:
            # Get transaction details
            transaction = supabase.table('transactions').select('*').eq('id', transaction_id).execute()
            if not transaction.data:
                return jsonify({'success': False, 'error': 'Transaction not found'})
            
            transaction = transaction.data[0]
            
            # Check if transaction is already processed
            if transaction['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Transaction already processed'})
            
            # Update transaction status
            result = supabase.table('transactions').update({
                'status': 'rejected'
            }).eq('id', transaction_id).execute()
            
            if not result.data:
                return jsonify({'success': False, 'error': 'Failed to update transaction status'})
            
            return jsonify({'success': True})
    except Exception as e:
        print(f"Error in reject_transaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port) 
