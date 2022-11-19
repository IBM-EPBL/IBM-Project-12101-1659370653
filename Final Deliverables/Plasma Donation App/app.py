from flask import Flask, render_template, flash, redirect, request, url_for, session, logging
import ibm_db
from flask_mail import Mail, Message
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
import random
import time
import os
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key=os.getenv(key="SECRET_KEY")

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv(key="MAIL_EMAIL")
app.config['MAIL_PASSWORD'] = os.getenv(key="MAIL_PASS")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

db_url = "DATABASE=%s;HOSTNAME=%s;PORT=%s;SECURITY=SSL;SSLServerCertificate=./DigiCertGlobalRootCA.crt;UID=%s;PWD=%s;"%(os.getenv(key="DB_NAME"),os.getenv(key="DB_HOST"), os.getenv(key="DB_PORT"), os.getenv(key="DB_USER"), os.getenv(key="DB_PASS"))
# print(db_url)
conn = ibm_db.connect(db_url, "", "")
mail = Mail(app)

@app.route('/')
def index():
    details = ibm_db.exec_immediate(conn, "SELECT * FROM CAMPS WHERE CAMP_DATE > CURRENT_DATE ORDER BY CAMP_DATE ASC")
    data = ibm_db.fetch_both(details)
    return render_template('home.html', camp=data)

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        bgroup = request.form["bgroup"]
        bpackets = request.form["bpackets"]
        fname = request.form["fname"]
        adress = request.form["adress"]
        email = request.form["email"]
        ibm_db.exec_immediate(conn,"INSERT INTO CONTACT(B_GROUP,C_PACKETS,F_NAME,ADRESS, EMAIL) VALUES('{}', {}, '{}', '{}', '{}')".format(bgroup, bpackets, fname, adress, email))
        ibm_db.exec_immediate(conn,"INSERT INTO NOTIFICATIONS(NB_GROUP,N_PACKETS,NF_NAME,NADRESS, EMAIL) VALUES('{}', {}, '{}', '{}', '{}')".format(bgroup, bpackets, fname, adress, email))

        flash('Your request is successfully sent to the Plasma Bank','success')
        return redirect(url_for('index'))

    return render_template('contact.html')


class RegisterForm(Form):
    name = StringField('Name', [validators.DataRequired(),validators.Length(min=1,max=25)])
    email = StringField('Email',[validators.DataRequired(),validators.Length(min=10,max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method  == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        e_id = name+str(random.randint(1111,9999))
        #Create cursor
        ibm_db.exec_immediate(conn,"INSERT INTO RECEPTION(E_ID,NAME,EMAIL,PASSWORD) VALUES('{}', '{}', '{}', '{}')".format(e_id, name, email, password))
        #Commit to DB
        #close connection
        flashing_message = "Success! You can log in with Employee ID " + str(e_id)
        flash( flashing_message,"success")

        return redirect(url_for('login'))

    return render_template('register.html',form = form)

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        e_id = request.form["e_id"]
        password_candidate = request.form["password"]

        # Create cursor

        print(e_id)

        # Get user by username
        result = ibm_db.exec_immediate(conn,"SELECT * FROM RECEPTION WHERE E_ID = '{}'".format(e_id))

        print(result)

        if result is not False:
            # Get stored hash
            data = ibm_db.fetch_both(result)
            password = data['PASSWORD']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['e_id'] = e_id

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection

        else:
            error = 'Employee ID not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login!', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    result = ibm_db.exec_immediate(conn,"SELECT * FROM BLOODBANK")
    print(result)
    details = ibm_db.fetch_both(result)
    # print("BLOOD GROUP", details['B_GROUP'])

    if result is not False:
        data = []
        while details is not False:
            data.append(details)
            details = ibm_db.fetch_both(result)
        return render_template('dashboard.html',details=data)
    else:
        msg = ' Plasma Bank is Empty '
        return render_template('dashboard.html',msg=msg)

@app.route('/donate', methods=['GET', 'POST'])
@is_logged_in
def donate():
    if request.method  == 'POST':
        # Get Form Fields
        dname = request.form["dname"]
        sex = request.form["sex"]
        age = request.form["age"]
        weight = request.form["weight"]
        address = request.form["address"]
        demail = request.form["demail"]


        #Inserting values into tables
        ibm_db.exec_immediate(conn,"INSERT INTO DONOR(DNAME,SEX,AGE,WEIGHT,ADDRESS,DEMAIL) VALUES('{}', '{}', {}, {}, '{}', '{}')".format(dname , sex, age, weight, address, demail))
        flash('Success! Donor details Added.','success')
        return redirect(url_for('donorlogs'))

    return render_template('donate.html')

@app.route('/donorlogs')
@is_logged_in
def donorlogs():
    result = ibm_db.exec_immediate(conn,"SELECT * FROM DONOR")
    details = ibm_db.fetch_both(result)

    if result is not False:
        data = []
        while details is not False:
            data.append(details)
            details = ibm_db.fetch_both(result)
        return render_template('donorlogs.html',logs=data)
    else:
        msg = ' No logs found '
        return render_template('donorlogs.html',msg=msg)


@app.route('/plasmaform',methods=['GET','POST'])
@is_logged_in
def plasmaform():
    if request.method  == 'POST':
        d_id = request.form["d_id"]
        blood_group = request.form["blood_group"]
        packets = request.form["packets"]

        ibm_db.exec_immediate(conn,"INSERT INTO BLOOD(D_ID,B_GROUP,PACKETS) VALUES({}, '{}', {})".format(d_id , blood_group, packets))
        result = ibm_db.exec_immediate(conn,"SELECT * FROM BLOODBANK WHERE B_GROUP = '{}'".format(blood_group))
        data = ibm_db.fetch_both(result)
        print("Data", data)
        if data is False:
            ibm_db.exec_immediate(conn,"INSERT INTO BLOODBANK(B_GROUP,TOTAL_PACKETS) VALUES('{}', {})".format(blood_group, packets))
        else:
            ibm_db.exec_immediate(conn,"UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS + {} WHERE B_GROUP = '{}'".format(packets,blood_group))
        flash('Success! Donor Plasma details Added.','success')
        return redirect(url_for('dashboard'))

    return render_template('bloodform.html')

@app.route('/camp/', methods=['GET','POST'])
@is_logged_in
def camp():
    if request.method == 'POST':
        # Get Form Fields
        camp_name = request.form["hname"]
        camp_date = request.form["date"]
        camp_place = request.form["place"]

        #Inserting values into tables
        ibm_db.exec_immediate(conn,"INSERT INTO CAMPS(CAMP_NAME,CAMP_DATE,CAMP_PLACE) VALUES('{}', '{}', '{}')".format(camp_name , camp_date, camp_place))
        flash('Success! Camp details Added.','success')
        return redirect(url_for('dashboard'))

    return render_template('camp.html')

@app.route('/notifications/')
@is_logged_in
def notifications():
    result = ibm_db.exec_immediate(conn,"SELECT * FROM NOTIFICATIONS")
    details = ibm_db.fetch_both(result)

    if result is not False:
        data = []
        while details is not False:
            data.append(details)
            details = ibm_db.fetch_both(result)
        return render_template('notification.html',requests=data)
    else:
        msg = ' No requests found '
        return render_template('notification.html',msg=msg)
    #close connectio

@app.route('/notifications/accept/<int:id>')
@is_logged_in
def accept(id):
    result = ibm_db.exec_immediate(conn,"SELECT * FROM NOTIFICATIONS WHERE N_ID = {}".format(id))
    data = ibm_db.fetch_assoc(result)
    print(data)
    result = ibm_db.exec_immediate(conn,"SELECT * FROM BLOODBANK WHERE B_GROUP = '{}' AND TOTAL_PACKETS >= {}".format(data['NB_GROUP'], data['N_PACKETS']))

    if result is not False:
        ibm_db.exec_immediate(conn,"UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS-{} WHERE B_GROUP = '{}'".format(data['N_PACKETS'],data['NB_GROUP']))
        ibm_db.exec_immediate(conn,"DELETE FROM NOTIFICATIONS WHERE N_ID = {}".format(id))
        msg = Message(
                'Request Accepted',
                sender =os.getenv(key="MAIL_EMAIL"),
                recipients = [data['EMAIL']]
               )
        msg.body = "Your request for plasma group {} is accepted. Please visit the plasma bank to collect the plasma.".format(data['NB_GROUP'])
        mail.send(msg)
        flash('Plasma Request Accepted','success')
        return redirect(url_for('notifications'))
    else:
        ibm_db.exec_immediate(conn,"DELETE FROM NOTIFICATIONS WHERE N_ID = {}".format(id))
        msg = Message(
                'Request Rejected',
                sender =os.getenv(key="MAIL_EMAIL"),
                recipients = [data['EMAIL']]
                )
        msg.body = "Your request for plasma group {} is rejected due to unavailability".format(data['NB_GROUP'])
        flash('Plasma Request Rejected','danger')
        return redirect(url_for('notifications'))

@app.route('/notifications/decline/<int:id>')
@is_logged_in
def decline(id):
    result = ibm_db.exec_immediate(conn,"SELECT * FROM NOTIFICATIONS WHERE N_ID = {}".format(id))
    data = ibm_db.fetch_assoc(result)
    ibm_db.exec_immediate(conn,"DELETE FROM NOTIFICATIONS WHERE N_ID = {}".format(id))
    msg = Message(
                'Request Rejected',
                sender =os.getenv(key="MAIL_EMAIL"),
                recipients = [data['EMAIL']]
                )
    msg.body = "Your request for plasma group {} is rejected due to unavailability".format(data['NB_GROUP'])
    print(msg)
    mail.send(msg)
    flash('Plasma Request Rejected','danger')
    return redirect(url_for('notifications'))


ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS RECEPTION(
E_ID VARCHAR(54) NOT NULL PRIMARY KEY,
NAME VARCHAR(100),
EMAIL VARCHAR(100),
PASSWORD VARCHAR(100),
REGISTER_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""")

ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS DONOR(
D_ID INT GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1) NOT NULL,
DNAME VARCHAR(50),
SEX VARCHAR(10),
AGE INT,
WEIGHT INT,
ADDRESS VARCHAR(150),
DEMAIL VARCHAR(100),
DONOR_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT PK_2 PRIMARY KEY(D_ID)
);""")


ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS BLOODBANK(
B_GROUP VARCHAR(4) NOT NULL,
TOTAL_PACKETS INT,
CONSTRAINT PK_3 PRIMARY KEY(B_GROUP)
);""")


ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS BLOOD(
B_CODE INT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
D_ID INT,
B_GROUP VARCHAR(4),
PACKETS INT,
CONSTRAINT PK_4 PRIMARY KEY(B_CODE)
);
""")


ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS CONTACT(
CONTACT_ID INT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
B_GROUP VARCHAR(4),
C_PACKETS INT,
F_NAME VARCHAR(50),
ADRESS VARCHAR(250),
EMAIL VARCHAR(100),
CONSTRAINT PK_5 PRIMARY KEY(CONTACT_ID)
);
""")


ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS NOTIFICATIONS(
N_ID INT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
NB_GROUP VARCHAR(4),
N_PACKETS INT,
NF_NAME VARCHAR(50),
NADRESS VARCHAR(250),
STATUS VARCHAR(10) DEFAULT 'PENDING',
EMAIL VARCHAR(100),
CONSTRAINT PK_6 PRIMARY KEY(N_ID)
);
""")

ibm_db.exec_immediate(conn, """CREATE TABLE IF NOT EXISTS CAMPS(
C_ID INT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
CAMP_NAME VARCHAR(100),
CAMP_DATE DATE,
CAMP_PLACE VARCHAR(250)
);
""")

ibm_db.commit(conn)

rs = ibm_db.exec_immediate(conn, "SELECT * FROM BLOODBANK")
print(rs)
print("App Started")
app.run(debug=True)
