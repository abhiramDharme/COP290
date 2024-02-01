#NEED TO ADD NIFTY50 IN DD LISTS

from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify   
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import pandas_ta as ta
from datetime import date
from dateutil.relativedelta import relativedelta
from flask_login import login_required, LoginManager, UserMixin, login_user, logout_user, current_user


app = Flask(__name__)
app.secret_key = 'black_sabbyath'  # Replace with your actual secret key

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

user = current_user

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    Contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    avg_buy_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)  # Update this periodically
    total_investment = db.Column(db.Float, nullable=False)
    realized_profit_loss = db.Column(db.Float, default=0.0)
    unrealized_profit_loss = db.Column(db.Float, default=0.0)

def calculate_total_realized_profit_loss(portfolio):
    return sum(stock.realized_profit_loss for stock in portfolio)

def calculate_total_unrealized_profit_loss(portfolio):
    return sum(stock.unrealized_profit_loss for stock in portfolio)

# Initialize Database within Application Context
with app.app_context():
    db.create_all()

fig=go.Figure()
filtered_stocks=pd.read_csv('nifty.csv')["Symbol"].to_list()
dropdown_stocks=filtered_stocks

def plot_graph_candle(stock1, startDate, endDate, rsi, vwaps):
    global fig
    fig=go.Figure()
    stock_data = yf.download(stock1, start=startDate, end=endDate)

    stock_data['rsi'] = ta.rsi(stock_data['Close'], length=14)

    stock_data['typical_price'] = (stock_data['High'] + stock_data['Low'] + stock_data['Close']) / 3

    stock_data['vwap'] = ta.sma(stock_data['typical_price'] * stock_data['Volume'], length=14) / ta.sma(stock_data['Volume'], length=14)

    if rsi=='true':
        fig.add_trace(go.Scatter(x=stock_data.index, 
                                 y=stock_data['rsi'],
                                 name='RSI',
                                 line=dict(color='red', 
                                           width=2)))
        
    if vwaps=='true':
        fig.add_trace(go.Scatter(x=stock_data.index, 
                                 y=stock_data['vwap'],
                                 name='VWAP',
                                 line=dict(color='green', 
                                           width=2)))

    candlestick = go.Candlestick(x=stock_data.index,
                                open=stock_data['Open'],
                                high=stock_data['High'],
                                low=stock_data['Low'],
                                close=stock_data['Close'],
                                name=stock1,
                                )

    fig.add_trace(candlestick)

    fig.update_xaxes(rangeslider_visible=True, 
    )
    fig.update_yaxes(title_text='Stock Price (INR)', 
    )

    # Update layout for better visibility
    fig.update_layout(title='Stock Price Variation for ' + stock1,
                    showlegend=True,
                    margin=dict(l=70, r=30, t=60, b=30),  # Adjust the left, right, top, and bottom margins
                    width=850,  # Set the width of the entire graph
                    height=540,  # Set the height of the entire graph
                    yaxis=dict(fixedrange=False)
                )

def plot_graph_line(stock, startDate, endDate):
    global fig
    stock_data = yf.download(stock, start=startDate, end=endDate)

    fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], 
                             mode='lines', 
                             name=stock))

    fig.update_layout(showlegend=True,
                      title="Absolute Price Comparison")

def plot_graph_relative(stocks, start_date, end_date):
    global fig
    fig = go.Figure()
    def fetch_stock_data(ticker, start_date, end_date):
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        return stock_data['Adj Close']

    stock_prices = {ticker: fetch_stock_data(ticker, start_date, end_date) for ticker in stocks}

    relative_rate_of_growth = {ticker: prices / prices.iloc[0] for ticker, prices in stock_prices.items()}

    for ticker, growth in relative_rate_of_growth.items():
        fig.add_trace(go.Scatter(x=growth.index, y=growth, 
                                 mode='lines', 
                                 name=ticker))

    fig.update_xaxes(rangeslider_visible=True)

    fig.update_layout(
        title='Relative Rate of Growth of Stocks',
        yaxis_title='Relative Rate of Growth',
        legend_title='Stocks',
        margin=dict(l=70, r=30, t=60, b=30),  # Adjust the left, right, top, and bottom margins
                    width=850,  # Set the width of the entire graph
                    height=540,  # Set the height of the entire graph
                    yaxis=dict(fixedrange=False)
    )

    return fig
    
final = []
final_df = pd.DataFrame()
keys_to_extract = ['symbol', 
                   'trailingPE', 
                   'dividendYield', 
                   'marketCap', 
                   'debtToEquity', 
                   'currentRatio', 
                   'trailingEps', 
                   'priceToBook', 
                   'earningsGrowth', 
                   'ebitdaMargins', 
                   'enterpriseToEbitda', 
                   'pegRatio', 
                   'returnOnEquity', 
                   'returnOnCapitalEmployed', 
                   'returnOnAssets', 
                   'priceToSalesTrailing12Months']

def fetch_stock_data():
    global final_df
    nifty_stocks = pd.read_csv("nifty.csv")
    nifty_stocks = nifty_stocks["Symbol"].tolist()

    for stock in nifty_stocks:
        symbol = stock + ".NS"
        ticker = yf.Ticker(symbol)
        stock_info = ticker.info
        filtered_info = {key: stock_info.get(key, None) for key in keys_to_extract}
        df = pd.DataFrame(filtered_info, index=[1])

        if not df.empty and not df.isna().all().all():
            final.append(df)

    if final:
        final_df = pd.concat(final)
    else:
        final_df = pd.DataFrame()


# Fetch stock data only if it hasn't been fetched before
if final_df.empty:
    fetch_stock_data()
    # print(final_df)
    filter_df = final_df[["symbol"]]


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/compare.html')
def compare():
    return render_template('compare.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        Name = request.form['Name']
        Contact = request.form['Contact']
        email = request.form['email']
        balance = 0.0

        new_user = User(username=username, password_hash=hashed_password, Name=Name, Contact=Contact, email=email, balance=round(balance,2))
        db.session.add(new_user)

        db.session.commit()

        new_user_portfolio = Portfolio(user_id=new_user.id, symbol='^NSEI', quantity=1, avg_buy_price=1, current_price=1, total_investment=1)
        db.session.add(new_user_portfolio)

        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    global fig
    global filtered_stocks
    fig=go.Figure()
    filtered_stocks=dropdown_stocks
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET'])
def dashboard():
    global fig
    global filtered_stocks
    global dropdown_stocks
    if 'user_id' in session:
        plot_graph_candle('^NSEI', startDate=date.today()-relativedelta(years=1), endDate=date.today(), rsi='false', vwaps='false')
        return render_template('welcome.html', username=session['username'], filtered_stocks=filtered_stocks, fig=fig.to_html(full_html=False), dropdown_stocks=dropdown_stocks, balance=round(current_user.balance,2))
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/process_data', methods=['POST'])
def process_data():
    global fig
    global filtered_stocks
    fig=go.Figure()
    stock1=request.form['stock1']
    stock2=request.form['stock2']
    stock3=request.form['stock3']
    stock4=request.form['stock4']
    endD=request.form['endDate']
    if endD == "":
        endD = date.today()
    startD=request.form['startDate']
    if startD == "":
        startD = endD -relativedelta(years=1)
    rsi=request.form['rsi']
    vwaps=request.form['vwaps']
    compare_type=request.form['compare_type']
    if compare_type == "select":
        compare_type = "absolute"

    if(compare_type=='absolute'):
        if(stock1=="^NSEI"):
            plot_graph_candle(stock1, startD, endD, rsi, vwaps)
        else:
            plot_graph_candle(stock1 + '.NS', startD, endD, rsi, vwaps)

        if(stock2!='select'):
            plot_graph_line(stock2 + '.NS', startD, endD)
        if(stock3!='select'):
            plot_graph_line(stock3 + '.NS', startD, endD)
        if(stock4!='select'):
            plot_graph_line(stock4 + '.NS', startD, endD)
    
    if(compare_type=='relative'):
        stocks=[]
        if(stock1!='select'): 
            if(stock1=="^NSEI"):
                stocks.append(stock1)
            else:
                stocks.append(stock1+'.NS')
        if(stock2!='select'): stocks.append(stock2+'.NS')
        if(stock3!='select'): stocks.append(stock3+'.NS')
        if(stock4!='select'): stocks.append(stock4+'.NS')
        fig=plot_graph_relative(stocks, startD, endD)

    
    
    return render_template('welcome.html', fig=fig.to_html(full_html=False), filtered_stocks=filtered_stocks, dropdown_stocks=dropdown_stocks)
        
@app.route('/filter', methods=['POST'])
def filter():
    global fig
    global filtered_stocks
    filtered_stocks = final_df['symbol'].tolist()
    if request.method == 'POST':
        pe_ratio = request.form.get('pe_ratio')
        dividend_yield = request.form.get('dividend_yield')
        market_cap = request.form.get('market_cap')
        market_cap_greater = request.form.get('market_cap_greater')
        debt_to_equity = request.form.get('debt_to_equity')
        current_ratio = request.form.get('current_ratio')
        eps = request.form.get('eps')
        price_to_book = request.form.get('price_to_book')
        earning_growth = request.form.get('earning_growth')
        ebitda_margin = request.form.get('ebitda_margin')
        entreprise_to_ebitda = request.form.get('entreprise_to_ebitda')
        peg_ratio = request.form.get('peg_ratio')
        roe = request.form.get('roe')
        roce = request.form.get('roce')
        roa = request.form.get('roa')
        price_to_sales = request.form.get('price_to_sales')

        filter_df = final_df  # Initialize with the complete DataFrame

        if pe_ratio is not None and pe_ratio != '':
            filter_df = filter_df[filter_df['trailingPE'] <= float(pe_ratio)]
        if dividend_yield is not None and dividend_yield != '':
            filter_df = filter_df[filter_df['dividendYield'] >= float(dividend_yield)]
        if market_cap is not None and market_cap != '':
            filter_df = filter_df[filter_df['marketCap'] >= float(market_cap)]
        if market_cap_greater is not None and market_cap_greater != '':
            filter_df = filter_df[filter_df['marketCap'] <= float(market_cap_greater)]
        if debt_to_equity is not None and debt_to_equity != '':
            filter_df = filter_df[filter_df['debtToEquity'] <= float(debt_to_equity)]
        if current_ratio is not None and current_ratio != '':
            filter_df = filter_df[filter_df['currentRatio'] >= float(current_ratio)]
        if eps is not None and eps != '':
            filter_df = filter_df[filter_df['trailingEps'] >= float(eps)]
        if price_to_book is not None and price_to_book != '':
            filter_df = filter_df[filter_df['priceToBook'] <= float(price_to_book)]
        if earning_growth is not None and earning_growth != '':
            filter_df = filter_df[filter_df['earningsGrowth'] >= float(earning_growth)]
        if ebitda_margin is not None and ebitda_margin != '':
            filter_df = filter_df[filter_df['ebitdaMargins'] >= float(ebitda_margin)]
        if entreprise_to_ebitda is not None and entreprise_to_ebitda != '':
            filter_df = filter_df[filter_df['enterpriseToEbitda'] <= float(entreprise_to_ebitda)]
        if peg_ratio is not None and peg_ratio != '':
            filter_df = filter_df[filter_df['pegRatio'] <= float(peg_ratio)]
        if roe is not None and roe != '':
            filter_df = filter_df[filter_df['returnOnEquity'] >= float(roe)]
        if roce is not None and roce != '':
            filter_df = filter_df[filter_df['returnOnCapitalEmployed'] >= float(roce)]
        if roa is not None and roa != '':
            filter_df = filter_df[filter_df['returnOnAssets'] >= float(roa)]
        if price_to_sales is not None and price_to_sales != '':
            filter_df = filter_df[filter_df['priceToSalesTrailing12Months'] <= float(price_to_sales)]
            

    filtered_stocks = filter_df['symbol'].tolist()

    return render_template('welcome.html', fig=fig.to_html(full_html=False), filtered_stocks=filtered_stocks, dropdown_stocks=dropdown_stocks)

@app.route('/profile')
def profile():
    if 'user_id' in session:
        # Fetch user details from the database based on the user's session ID
        user = User.query.get(session['user_id'])

        if user:
            user_details = {
                'username': user.username,
                'name': user.Name,
                'contact_number': user.Contact,
                'email': user.email  # Update this if you have an email field in your User model
                # Add more user details as needed
            }

            return render_template('profile.html', username=user_details['username'], user_details=user_details)
        else:
            # Handle the case when the user is not found in the database
            flash('User not found.', 'error')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    

@app.route('/contact', methods=['POST', 'GET'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')


        flash('Your message has been submitted. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/funds')
def funds():
    return render_template('funds.html', username=session['username'], balance=round(current_user.balance, 2))

@app.route('/add_funds', methods=['POST'])
@login_required
def add_funds():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        current_user.balance += amount

        db.session.commit()

        flash(f"Funds added successfully: +{amount} INR", 'success')

        return render_template('funds.html', username=current_user.username, balance=round(current_user.balance, 2))

@app.route('/withdraw_funds', methods=['POST'])
@login_required
def withdraw_funds():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if current_user.balance >= amount:
            current_user.balance -= amount

            session['balance'] = current_user.balance

            db.session.commit()

            flash(f"Funds withdrawn successfully: -{amount} INR", 'success')
        else:
            flash("Insufficient funds for withdrawal.", 'error')

        return render_template('funds.html', username=current_user.username, balance=round(current_user.balance,2))

@app.route('/portfolio', methods=['GET', 'POST'])
@login_required
def portfolio():
    user_portfolio = Portfolio.query.filter_by(user_id=current_user.id).all()
    total_realized_profit_loss = calculate_total_realized_profit_loss(user_portfolio)
    total_unrealized_profit_loss = calculate_total_unrealized_profit_loss(user_portfolio)
    return render_template('portfolio.html',
                           username=current_user.username,
                           balance=current_user.balance,
                           portfolio=user_portfolio,
                           total_realized_profit_loss=total_realized_profit_loss,
                           total_unrealized_profit_loss=total_unrealized_profit_loss,
                           dropdown_stocks_portfolio=final_df['symbol'].tolist())


@app.route('/buy_sell', methods=['POST', 'GET'])
@login_required
def buy_sell():
    if request.method == 'POST':
        action = request.form['action']
        symbol = request.form['stock1']
        quantity = request.form['quantity']
        if quantity == "": quantity=1
        quantity=int(quantity)
        ticker = yf.Ticker(symbol)
        stock_info = ticker.info
        print(stock_info['currentPrice'])

        current_price = stock_info['currentPrice']

        user_portfolio = Portfolio.query.filter_by(user_id=current_user.id, symbol=symbol).first()

        if action == 'buy':
            total_investment = quantity * current_price

            if current_user.balance >= total_investment:
                current_user.balance -= total_investment

                if user_portfolio:
                    total_existing_investment = user_portfolio.total_investment + total_investment
                    new_avg_buy_price = (user_portfolio.quantity * user_portfolio.avg_buy_price + total_investment) / (user_portfolio.quantity + quantity)
                    user_portfolio.quantity += quantity
                    user_portfolio.avg_buy_price = new_avg_buy_price
                    user_portfolio.total_investment = total_existing_investment
                    user_portfolio.current_price = current_price
                else:
                    user_portfolio = Portfolio(user_id=current_user.id, symbol=symbol, quantity=quantity,
                                               avg_buy_price=current_price, current_price=current_price,
                                               total_investment=total_investment)
                    db.session.add(user_portfolio)

                flash(f"Bought {quantity} shares of {symbol} successfully!", 'success')
            else:
                flash("Insufficient funds for the purchase.", 'error')

        elif action == 'sell':
            if user_portfolio and user_portfolio.quantity >= quantity:
                user_portfolio.quantity -= quantity
                user_portfolio.current_price = current_price
                total_sale = quantity * current_price
                realized_profit_loss = total_sale - (quantity * user_portfolio.avg_buy_price)
                user_portfolio.realized_profit_loss += realized_profit_loss
                current_user.balance += total_sale
                flash(f"Sold {quantity} shares of {symbol} successfully!", 'success')

                if user_portfolio.quantity == 0:
                    db.session.delete(user_portfolio)
            else:
                flash("Insufficient shares for the sale or stock not found in the portfolio.", 'error')

        db.session.commit()

    user_portfolio = Portfolio.query.filter_by(user_id=current_user.id).all()

    return render_template('portfolio.html',
                    username=current_user.username,
                    balance=round(current_user.balance,2),
                    portfolio=user_portfolio,
                    dropdown_stocks_portfolio=final_df['symbol'].tolist())


if __name__ == '__main__':
    app.run(debug=True)
