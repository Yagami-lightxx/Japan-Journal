from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-key-for-dev-only')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    entries = db.relationship('JournalEntry', backref='author', lazy=True)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location = db.Column(db.String(100))
    mood = db.Column(db.String(50))
    image = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        entries = JournalEntry.query.filter_by(user_id=session['user_id']).order_by(JournalEntry.date_posted.desc()).limit(3).all()
        return render_template('index.html', entries=entries)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    if 'user_id' not in session:
        flash('Please log in to add journal entries.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        location = request.form['location']
        mood = request.form['mood']
        
        # Handle image upload
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        
        entry = JournalEntry(
            title=title,
            content=content,
            location=location,
            mood=mood,
            image=image,
            user_id=session['user_id']
        )
        
        db.session.add(entry)
        db.session.commit()
        
        flash('Journal entry added successfully!', 'success')
        return redirect(url_for('view_entries'))
    
    return render_template('add_entry.html')

@app.route('/entries')
def view_entries():
    if 'user_id' not in session:
        flash('Please log in to view your journal entries.', 'warning')
        return redirect(url_for('login'))
    
    entries = JournalEntry.query.filter_by(user_id=session['user_id']).order_by(JournalEntry.date_posted.desc()).all()
    return render_template('entries.html', entries=entries)

@app.route('/entry/<int:entry_id>')
def view_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the user owns the entry
    if 'user_id' not in session or entry.user_id != session['user_id']:
        flash('You can only view your own journal entries.', 'danger')
        return redirect(url_for('home'))
    
    return render_template('entry.html', entry=entry)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
