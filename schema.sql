-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables and policies
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS referrals CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS investments CASCADE;
DROP TABLE IF EXISTS stocks CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop existing functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS add_to_wallet(UUID, DECIMAL) CASCADE;
DROP FUNCTION IF EXISTS subtract_from_wallet(UUID, DECIMAL) CASCADE;

-- Create tables
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    aadhaar TEXT NOT NULL UNIQUE,
    mobile TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    wallet_balance DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE stocks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    package DECIMAL(10,2) NOT NULL,
    daily_return DECIMAL(10,2) NOT NULL,
    total_return DECIMAL(10,2) NOT NULL,
    tenure_days INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE TABLE investments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    stock_id UUID REFERENCES stocks(id),
    package DECIMAL(10,2) NOT NULL,
    daily_return DECIMAL(10,2) NOT NULL,
    total_return DECIMAL(10,2) NOT NULL,
    tenure_days INTEGER NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE TABLE transactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    type TEXT NOT NULL CHECK (type IN ('deposit', 'withdraw', 'referral')),
    amount DECIMAL(10,2) NOT NULL,
    utr_number TEXT,
    sender_name TEXT,
    account_details TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE TABLE claims (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    investment_id UUID REFERENCES investments(id),
    user_id UUID REFERENCES users(id),
    amount DECIMAL(10,2) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE TABLE referrals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    referrer_id UUID REFERENCES users(id),
    referred_name TEXT NOT NULL,
    referred_aadhaar TEXT NOT NULL,
    stock_amount DECIMAL(10,2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE TABLE support_tickets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    query_type TEXT NOT NULL,
    complaint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'resolved')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Insert initial stock data
INSERT INTO stocks (name, package, daily_return, total_return, tenure_days) VALUES
('TATA Motors', 2000, 100, 9000, 90),
('TATA Electrical', 3000, 120, 21600, 180),
('TATA Technologies', 3500, 125, 22500, 180),
('TATA Consultancy Services', 4000, 160, 48000, 365),
('TATA Steel', 5000, 200, 60000, 365),
('TATA Chemicals', 10000, 500, 120000, 365);

-- Create RLS policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Enable insert for all users" ON users
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable select for all users" ON users
    FOR SELECT USING (true);

CREATE POLICY "Enable update for all users" ON users
    FOR UPDATE USING (true);

-- Stocks policies
CREATE POLICY "Enable select for all users" ON stocks
    FOR SELECT USING (true);

-- Investments policies
CREATE POLICY "Enable select for all users" ON investments
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON investments
    FOR INSERT WITH CHECK (true);

-- Transactions policies
CREATE POLICY "Enable select for all users" ON transactions
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON transactions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON transactions
    FOR UPDATE USING (true);

-- Claims policies
CREATE POLICY "Enable select for all users" ON claims
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON claims
    FOR INSERT WITH CHECK (true);

-- Referrals policies
CREATE POLICY "Enable select for all users" ON referrals
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON referrals
    FOR INSERT WITH CHECK (true);

-- Support tickets policies
CREATE POLICY "Enable select for all users" ON support_tickets
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON support_tickets
    FOR INSERT WITH CHECK (true);

-- Create functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_referrals_updated_at
    BEFORE UPDATE ON referrals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_support_tickets_updated_at
    BEFORE UPDATE ON support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to add amount to wallet
CREATE OR REPLACE FUNCTION add_to_wallet(user_id UUID, amount DECIMAL)
RETURNS DECIMAL AS $$
DECLARE
    current_balance DECIMAL;
BEGIN
    SELECT wallet_balance INTO current_balance
    FROM users
    WHERE id = user_id;
    
    RETURN current_balance + amount;
END;
$$ LANGUAGE plpgsql;

-- Create function to subtract amount from wallet
CREATE OR REPLACE FUNCTION subtract_from_wallet(user_id UUID, amount DECIMAL)
RETURNS DECIMAL AS $$
DECLARE
    current_balance DECIMAL;
BEGIN
    SELECT wallet_balance INTO current_balance
    FROM users
    WHERE id = user_id;
    
    IF current_balance < amount THEN
        RAISE EXCEPTION 'Insufficient balance';
    END IF;
    
    RETURN current_balance - amount;
END;
$$ LANGUAGE plpgsql;

-- Create admin user
INSERT INTO users (name, aadhaar, mobile, password, wallet_balance, is_admin)
VALUES ('Admin', '000000000000', '9999999999', 'admin123', 0, TRUE); 