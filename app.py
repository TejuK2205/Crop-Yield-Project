from pymysql.cursors import DictCursor 
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
 # Import DictCursor for dictionary results

app = Flask(__name__)
app.secret_key = 'aws_project'  # Used for flashing messages and session management

# MySQL connection details using PyMySQL
db_config = {
    'host': 'database-2.chcjj1i2dmdd.us-east-1.rds.amazonaws.com',
    'user': 'admin',  # replace with your MySQL username
    'password': 'Teju2205@',  # replace with your MySQL password
    'database': 'crop_yield_db'  # replace with your MySQL database name
}

# Initialize the database connection
def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(DictCursor)  # Use DictCursor here for dictionary-style rows

        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user:
            # Check if the password matches
            if password == user['password']:  # No password hashing for simplicity
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect password', 'danger')
        else:
            flash('User not found', 'danger')

        cursor.close()
        conn.close()

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Simple password validation
        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
            flash('Password must be at least 8 characters long, contain numbers and letters', 'danger')
            return render_template('signup.html')

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(DictCursor)  # Use DictCursor here for dictionary-style rows

        # Check if the email already exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Email already exists', 'danger')
            return render_template('signup.html')

        # Insert the new user into the database
        cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Retrieve the logged-in user's name
    user_name = session['user_name']
    return render_template('homepage.html', user_name=user_name)


@app.route('/store_data', methods=['GET', 'POST'])
def store_data():
    if request.method == 'POST':
        # Retrieve data from the form
        state_name = request.form['state_name']
        district_name = request.form['district_name']
        crop_year = request.form['crop_year']
        season = request.form['season']
        crop = request.form['crop']
        area = request.form['area']
        production = request.form['production']
        yields = request.form['yield']

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Insert data into the farmer_data table
            cursor.execute('''
                INSERT INTO crop_statistics (state, district, crop_year, season, crop, area, production, yield)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (state_name, district_name, crop_year, season, crop, area, production, yields))

            # Commit the transaction
            conn.commit()

            flash('Data stored successfully!', 'success')

        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            flash(f'Error storing data: {str(e)}', 'danger')

        finally:
            # Close the cursor and connection
            cursor.close()
            conn.close()

        return redirect(url_for('store_data'))  # Redirect back to the store_data page

    return render_template('store_data.html')
  # Use non-GUI backend for saving figures
@app.route('/analyze_data')
def analyze_data():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('You need to log in first', 'danger')
        return redirect(url_for('login'))
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Fetch data from all tables
    cursor.execute('SELECT * FROM crop_statistics')
    crop_data = cursor.fetchall()
    
    cursor.execute('SELECT * FROM farmer_data')
    farmer_data = cursor.fetchall()
    
    cursor.execute('SELECT * FROM rainfall_data')
    rainfall_data = cursor.fetchall()

    cursor.execute('SELECT * FROM crop_data')
    crop_conditions_data = cursor.fetchall()

    # Convert the results into Pandas DataFrames
    crop_df = pd.DataFrame(crop_data)
    farmer_df = pd.DataFrame(farmer_data)
    rainfall_df = pd.DataFrame(rainfall_data)
    crop_conditions_df = pd.DataFrame(crop_conditions_data)

    # Perform data analysis and generate plots
    analysis_results = {}

    # 1. Average Yield per Crop per Season
    avg_yield_per_crop_season = crop_df.groupby(['crop', 'season'])['yield'].mean().reset_index()

    # Plot: Average Yield per Crop per Season
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='crop', y='yield', hue='season', data=avg_yield_per_crop_season, ax=ax)
    ax.set_title('Average Yield per Crop per Season')
    plt.xticks(rotation=45)
    avg_yield_plot = save_fig(fig)

    # 2. Total Area Under Different Crops
    total_area_per_crop = crop_df.groupby('crop')['area'].sum().reset_index()

    # Plot: Total Area Under Different Crops
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='crop', y='area', data=total_area_per_crop, ax=ax)
    ax.set_title('Total Area Under Different Crops')
    plt.xticks(rotation=45)
    area_plot = save_fig(fig)

    # 3. Production vs Area for Each Crop
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(x='area', y='production', hue='crop', data=crop_df, ax=ax)
    ax.set_title('Production vs Area for Each Crop')
    production_area_plot = save_fig(fig)

    # 4. Statewise Annual Rainfall
    state_rainfall = rainfall_df.groupby('state_UT')['annual_rainfall'].sum().reset_index()

    # Plot: Statewise Annual Rainfall
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='state_UT', y='annual_rainfall', data=state_rainfall, ax=ax)
    ax.set_title('Statewise Annual Rainfall')
    plt.xticks(rotation=45)
    rainfall_plot = save_fig(fig)

    # 5. Average Nitrogen, Potassium, and Phosphorus Levels for Crops
    avg_nutrients = crop_conditions_df.groupby('crop_type')[['nitrogen', 'potassium', 'phosphorous']].mean().reset_index()

    # Plot: Average Nitrogen, Potassium, and Phosphorus Levels for Crops
    fig, ax = plt.subplots(figsize=(10, 6))
    avg_nutrients.set_index('crop_type').plot(kind='bar', ax=ax)
    ax.set_title('Average Nutrient Levels for Crops')
    ax.set_ylabel('Average Levels')
    nutrients_plot = save_fig(fig)

    # 6. Average Yield vs Soil Moisture
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(x='soil_moisture', y=crop_df['yield'], hue='crop_type', data=crop_conditions_df, ax=ax)
    ax.set_title('Average Yield vs Soil Moisture')
    yield_soil_moisture_plot = save_fig(fig)

    # Close all figures explicitly
    plt.close('all')

    # Add the plots to the analysis results dictionary
    analysis_results['avg_yield_plot'] = avg_yield_plot
    analysis_results['area_plot'] = area_plot
    analysis_results['production_area_plot'] = production_area_plot
    analysis_results['rainfall_plot'] = rainfall_plot
    analysis_results['nutrients_plot'] = nutrients_plot
    analysis_results['yield_soil_moisture_plot'] = yield_soil_moisture_plot

    # Close the database connection
    cursor.close()
    conn.close()

    return render_template('analyze_data.html', analysis_results=analysis_results)

def save_fig(fig):
    """
    Save the plot to a BytesIO object and convert it to a base64 string
    """
    img = BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf8')


@app.route('/modify_data', methods=['GET', 'POST'])
def modify_data():
    if 'user_id' not in session:
        flash('You need to log in first', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(DictCursor)  # Correct cursor setup

    # Fetch user and farmer data
    cursor.execute('SELECT name, email, password FROM users WHERE id = %s', (user_id,))
    user_data = cursor.fetchone()

    cursor.execute('SELECT crop, crop_year, area, production, yield_per_hectare FROM farmer_data WHERE user_id = %s', (user_id,))
    farmer_data = cursor.fetchone()

    if request.method == 'POST':
        # Get data from form
        name = request.form['name']
        email = request.form['email']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        crop = request.form['crop']
        crop_year = request.form['crop_year']
        area = float(request.form['area'])
        production = float(request.form['production'])
        yield_per_hectare = float(request.form['yield_per_hectare'])

        # Check if the current password is correct
        if user_data['password'] != current_password:
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('modify_data'))

        # Update password if new password is provided
        if new_password:
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (new_password, user_id))

        # Update name and email
        cursor.execute('UPDATE users SET name = %s, email = %s WHERE id = %s', (name, email, user_id))

        # Update farmer data
        cursor.execute('''
            UPDATE farmer_data
            SET crop = %s, crop_year = %s, area = %s, production = %s, yield_per_hectare = %s
            WHERE user_id = %s
        ''', (crop, crop_year, area, production, yield_per_hectare, user_id))

        flash('Data updated successfully!', 'success')
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('index'))

    cursor.close()
    conn.close()

    return render_template('modify_data.html', user_data=user_data, farmer_data=farmer_data)

@app.route('/logout')
def logout():
    session.pop('farmer_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

