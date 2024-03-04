from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
import config

app = Flask(__name__)
app.secret_key = config.SQL_SECRET
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instagram_token = db.Column(db.String(255), nullable=False)
    page_id = db.Column(db.String(255), nullable=False)
    page_name = db.Column(db.String(255), nullable=False)
    page_access_token = db.Column(db.String(255), nullable=False)
    instagram_business_account_id = db.Column(db.String(255), nullable=False)

# Construct the Login URL
def construct_login_url():
    client_id = config.CLIENT_ID
    redirect_uri = f'{config.HOSTED_APP_URL}/oauth_callback'
    scope = 'instagram_basic,instagram_content_publish,instagram_manage_comments,instagram_manage_insights,pages_show_list,pages_read_engagement'
    login_url = f'https://www.facebook.com/dialog/oauth?client_id={client_id}&display=page&extras={{"setup":{{"channel":"IG_API_ONBOARDING"}}}}&redirect_uri={redirect_uri}&response_type=token&scope={scope}'
    return login_url

# Assign the URL to a Button
@app.route('/')
def home():
    login_url = construct_login_url()
    return render_template('index.html', login_url=login_url)

# Capture User access token and render reel form
@app.route('/oauth_callback')
def oauth_callback():
    access_token = request.args.get('access_token')
    if access_token:
        page_data = get_user_page_data(access_token)
        if page_data:
            store_user_data(access_token, page_data)
            return redirect(url_for('profile'))
        else:
            return 'Error: Failed to retrieve user page data'
    else:
        return 'Error: No access token provided'

# Get the User - Page, Page Access Token, and Instagram Business Account
def get_user_page_data(access_token):
    url = 'https://graph.facebook.com/v19.0/me/accounts'
    params = {
        'fields': 'id,name,access_token,instagram_business_account',
        'access_token': access_token
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            page_data = data['data'][0]  
            return page_data
    return None

# Store the user data in the DB
def store_user_data(access_token, page_data):
    user = User(
        instagram_token=access_token,
        page_id=page_data['id'],
        page_name=page_data['name'],
        page_access_token=page_data['access_token'],
        instagram_business_account_id=page_data['instagram_business_account']['id']
    )
    db.session.add(user)
    db.session.commit()

# Upload reel to Instagram
@app.route('/upload_reel', methods=['POST'])
def upload_reel():
    user = User.query.first()
    if user:
        access_token = user.instagram_token
        video_url = request.form['video']
        caption = request.form['caption']
        success, message = upload_reel_to_instagram(access_token, video_url, caption)
        if success:
            return 'Reel uploaded successfully!'
        else:
            return f'Error uploading reel: {message}'
    else:
        return 'Error: No user data found'


# Function to upload reel to Instagram
def upload_reel_to_instagram(access_token, video_url, caption):
    url = 'https://graph.instagram.com/me/media'
    params = {
        'access_token': access_token,
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return True, "Post uploaded successfully"
    else:
        return False, "Error uploading post: {}".format(response.text)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
