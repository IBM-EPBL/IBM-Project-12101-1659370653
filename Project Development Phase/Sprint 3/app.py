from flask import Flask, render_template, flash, redirect, request, url_for, session, logging
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
import random
from functools import wraps


app = Flask(__name__)
app.secret_key='some secret key'


#Config MySQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='password'
app.config['MYSQL_DB']='bloodbank'
app.config['MYSQL_CURSORCLASS']='DictCursor'

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'joelrichard808@gmail.com'
app.config['MAIL_PASSWORD'] = 'qlwagnsyjvjytssa'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mysql =  MySQL(app)
mail = Mail(app)

@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM BLOODBANK")
    details = cur.fetchall()

    if result>0:
        return render_template('dashboard.html',details=details)
    else:
        msg = ' Blood Bank is Empty '
        return render_template('dashboard.html',msg=msg)
    #close connection
    cur.close()

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

        #create a cursor
        cur = mysql.connection.cursor()

        #Inserting values into tables
        cur.execute("INSERT INTO DONOR(DNAME,SEX,AGE,WEIGHT,ADDRESS,DEMAIL) VALUES(%s, %s, %s, %s, %s, %s)",(dname , sex, age, weight, address, demail))
        #Commit to DB
        mysql.connection.commit()
        #close connection
        cur.close()
        flash('Success! Donor details Added.','success')
        return redirect(url_for('donorlogs'))

    return render_template('donate.html')

@app.route('/donorlogs')
@is_logged_in
def donorlogs():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM DONOR")
    logs = cur.fetchall()

    if result>0:
        return render_template('donorlogs.html',logs=logs)
    else:
        msg = ' No logs found '
        return render_template('donorlogs.html',msg=msg)
    #close connection
    cur.close()


@app.route('/bloodform',methods=['GET','POST'])
@is_logged_in
def bloodform():
    if request.method  == 'POST':
        # Get Form Fields
        d_id = request.form["d_id"]
        blood_group = request.form["blood_group"]
        packets = request.form["packets"]

        #create a cursor
        cur = mysql.connection.cursor()

        #Inserting values into tables
        cur.execute("INSERT INTO BLOOD(D_ID,B_GROUP,PACKETS) VALUES(%s, %s, %s)",(d_id , blood_group, packets))
        cur.execute("SELECT * FROM BLOODBANK WHERE B_GROUP = %s",(blood_group,))
        data = cur.fetchone()
        if data is None:
            cur.execute("INSERT INTO BLOODBANK(B_GROUP,TOTAL_PACKETS) VALUES(%s, %s)",(blood_group, packets))
        else:
            cur.execute("UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS + %s WHERE B_GROUP = %s",(packets,blood_group))
        #Commit to DB
        mysql.connection.commit()
        #close connection
        cur.close()
        flash('Success! Donor Blood details Added.','success')
        return redirect(url_for('dashboard'))

    return render_template('bloodform.html')


@app.route('/notifications/')
@is_logged_in
def notifications():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM NOTIFICATIONS")
    requests = cur.fetchall()

    if result>0:
        return render_template('notification.html',requests=requests)
    else:
        msg = ' No requests found '
        return render_template('notification.html',msg=msg)
    #close connection
    cur.close()

@app.route('/notifications/accept/<int:id>')
@is_logged_in
def accept(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM NOTIFICATIONS WHERE N_ID = %s",(id,))

    data = cur.fetchone()

    cur.execute("SELECT * FROM BLOODBANK WHERE B_GROUP = %s AND TOTAL_PACKETS >= %s",(data['NB_GROUP'], data['N_PACKETS']))

    if cur.fetchone() is not None:
        cur.execute("UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS-%s WHERE B_GROUP = %s",(data['N_PACKETS'],data['NB_GROUP']))
        cur.execute("DELETE FROM NOTIFICATIONS WHERE N_ID = %s",(id,))
        mysql.connection.commit()
        cur.close()
        msg = Message(
                'Request Accepted',
                sender ='joelrichard808@gmail.com',
                recipients = [data['EMAIL']]
               )
        msg.body = "Your request for blood group {} is accepted. Please visit the blood bank to collect the blood.".format(data['NB_GROUP'])
        mail.send(msg)
        flash('Blood Request Accepted','success')
        return redirect(url_for('notifications'))
    else:
        cur.execute("DELETE FROM NOTIFICATIONS WHERE N_ID = %s",(id,))
        mysql.connection.commit()
        cur.close()
        msg = Message(
                'Request Rejected',
                sender ='joekrichard808@gmail.com',
                recipients = [data['EMAIL']]
                )
        msg.body = "Your request for blood group {} is rejected due to unavailability".format(data['NB_GROUP'])
        flash('Blood Request Rejected','danger')
        return redirect(url_for('notifications'))

@app.route('/notifications/decline/<int:id>')
@is_logged_in
def decline(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM NOTIFICATIONS WHERE N_ID = %s",(id,))
    data = cur.fetchone()
    cur.execute("DELETE FROM NOTIFICATIONS WHERE N_ID = %s",(id,))
    mysql.connection.commit()
    cur.close()
    msg = Message(
                'Request Rejected',
                sender ='joekrichard808@gmail.com',
                recipients = [data['EMAIL']]
                )
    msg.body = "Your request for blood group {} is rejected due to unavailability".format(data['NB_GROUP'])
    print(msg)
    mail.send(msg)
    flash('Blood Request Rejected','danger')
    return redirect(url_for('notifications'))

if __name__ == '__main__':
    app.run(debug=True)
