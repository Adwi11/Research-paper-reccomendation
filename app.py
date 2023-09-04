from flask import Flask,render_template,request,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
import mysql.connector
from bs4 import BeautifulSoup
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import time
import re
from validate_email import validate_email

mydb = mysql.connector.connect(host='localhost', user='root', passwd='root')
app = Flask(__name__)  # create your Flask instance '__name__' used as the root of the application 
app.secret_key = '77$6%$81@$112 '
cursor = mydb.cursor()

class User:
    def __init__(self, email, interests):
        self.email = email
        self.interests = interests


@app.route('/')
def index():
    
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    interests = request.form.getlist('interests')
    user = User(email=email, interests=interests)

    #  makeshift solution to empty interests 
    if user.interests[0]=='':
        flash("Interests cannot be empty !",'error')
        return render_template('register.html')
    
    if not validate_email(user.email):
        flash("Invalid or unreachable email address!", 'error')
        return render_template('register.html')
    
    try:
        cursor = mydb.cursor()
        count_query = f"SELECT COUNT(*) FROM {'formresponse.form'}"
        cursor.execute(count_query)
        row_count = cursor.fetchone()[0]
        row_count+=1
        add_user_query = f"INSERT INTO `formresponse`.`form` (`Pid`, `Email`, `Interests`) VALUES('{row_count}', '{user.email}', '{user.interests[0]}')"
        cursor.execute(add_user_query)

        # Commit the changes
        mydb.commit()
        # send_recommendations()   
        flash('Registration successful!', 'success')
    except mysql.connector.Error as e:
        error_message = str(e)
        if 'Duplicate' in error_message:
            flash('This email has already registered.', 'error')
        else:
            flash('Error occurred during registration.', 'error')
        
        

    return render_template('register.html') 


app.route('/send_recommendations')
def send_recommendations():
    cursor = mydb.cursor()
    count_query = f"SELECT COUNT(*) FROM {'formresponse.form'}"
    cursor.execute(count_query)
    row_count = cursor.fetchone()[0]
    for pid in range(1,row_count+1):
     
        cursor = mydb.cursor()
        interests_query = f"SELECT Interests FROM formresponse.form where Pid={pid}"
        cursor.execute(interests_query)
        interests = cursor.fetchone()[0].split(',')

        search_url = "https://arxiv.org/search/"
        params = {
            "query": ' , '.join(interests),  # Combine user interests with OR operator for the search query (you can straight up use the string recieved)
            "order": "announced_date_first",  # Sort the results by submission date (newest first)
            "searchtype": "all",
            "abstracts": "show",
            "size": "50"

        }
        response = requests.get(search_url, params=params)
        # print(response.url) #FOR TESTING CONTENT
        soup = BeautifulSoup(response.content, "html.parser")
        results = soup.find_all("li", class_="arxiv-result") 
        # print(results)
        recommendations = []
        print(results[:4])
        for result in results[:4]:
            title = result.find("p", class_="title is-5 mathjax").text.strip()
            
            authors = result.find("p", class_="authors").text.strip()
            
            abstract = result.find("p", class_="abstract").text.strip()
            link = result.find("a")["href"]

            paper = {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "link": "https://arxiv.org" + link
        }
            recommendations.append(paper)
        
        email_query = f"SELECT Email FROM formresponse.form where Pid={pid}"
        cursor.execute(email_query)
        email = cursor.fetchone()[0]
        # print('recommendations:',recommendations)
        send_email(email,recommendations)
    
    return "Recommendation cycle activated! Thank You"

def send_email(email,recommendations):
    smtp_host = 'smtp-mail.outlook.com'  # Replace with your SMTP server host
    smtp_port = 587  # Replace with your SMTP server port
    smtp_username = 'pyTest123@outlook.com'  # Replace with your SMTP server username
    smtp_password = 'pyest123'

    message = MIMEMultipart()
    message['From'] = smtp_username  # Replace with your email address
    message['To'] = email
    message['Subject'] = 'Daily Research Paper Recommendations From NeedForRead'
    # print(recommendations)
    body = f'<h1>Research Paper Recommendations</h1>'
    for recommendation in recommendations:
        body += f'<h3>{recommendation["title"]}</h3>'
        body += f'<p>Authors: {recommendation["authors"]}</p>'
        body += f'<p>{recommendation["abstract"]}</p>'
    message.attach(MIMEText(body, 'html'))
    # print(email)
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(message['From'], message['To'], message.as_string())
  
#// TODO ADDING AI
#//TODO: Previously sent research papers 
#// TODO ADD CONRIBUTORS PORTAL TYPE SCENE
#//TODO: Create new landing page 
#//TODO: Click to Unsubscribe

if __name__=='__main__':
   
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_recommendations, 'cron', hour=00, minute=int('42'))
    scheduler.start()
    app.run(debug=True)
    



