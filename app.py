import functions
from functions import conn, app
import re

from flask import Flask, render_template, request, flash, url_for, session, redirect
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import json

import wordpredict

app.secret_key = 'boobies'

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')


@app.route('/', methods=['GET', 'POST'])
def home():
    print("should be logging in")
    if 'loggedin' in session:
        return redirect(url_for('listitems'))    
    return render_template('login.html')
    


@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(username)
        print(password)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        print("account - " + str(account))
        if account:
            password_rs = account['password']
            print(password_rs)
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                session['email'] = account['email']
                session['chosenList'] = "General"
                print("{0}, {1}, {2}, {3} ".format(session['loggedin'], session['id'], session['username'],
                                                   session['email']))

                return redirect(url_for('listitems'))

            else:
                flash('Incorrect username/password')
                print("shit")
                return render_template('login.html')
    return render_template('login.html')


@app.route('/listitems', methods=['GET', 'POST'])
def listitems():
    if session['username']:
        if request.method == 'GET':
            username = session['username']
            print(username + ' logged in')
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            sql_string_get_list = '''
                SELECT listitems.item
                FROM listitems
                FULL JOIN listnames ON listitems.listnameid = listnames.id
                FULL JOIN users ON listnames.userid = users.id
                WHERE listnames.listname = '{}'
                AND users.id = (SELECT id FROM users WHERE username = '{}');
            '''.format(session['chosenList'], session['username'])

            cursor.execute(sql_string_get_list)
            conn.commit()
            list_items = cursor.fetchall()
            # print("in listItems.html")
            # print(sql_string_get_list)
            # print(list_items)
            new_items = functions.get_user_list_names()
            print(new_items)
            return render_template('listitems.html', list_items=list_items, new_items=new_items)
            
        else:
            print("not updating")
        return render_template('listitems.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'username' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        _hashed_password = generate_password_hash(password)
        cursor.execute("SELECT * FROM users WHERE username = '{}'".format(username))
        account = cursor.fetchone()
        if account:
            flash('Account already exists! Please log in.')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # adding user
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES ('{}','{}', '{}')".format(username, email,
                                                                                                _hashed_password))
            # getting new user id
            cursor.execute("SELECT id FROM users WHERE username = '{}'".format(username))
            conn.commit()
            resp = cursor.fetchone()
            # print(resp)
            # print("id = " + resp[0])
            # adding a general list to the new user's account
            cursor.execute("INSERT INTO listnames(listname, userid) VALUES ('General' , '{}')".format(resp['id']))
            conn.commit()
            # flash('You have been registered!')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    # session.delete()
    return redirect(url_for('login'))


@app.route('/add_listitems', methods=['GET', 'POST'])
def add_listitems():
    print("adding list item to db")
    if request.method == 'POST' and 'input_text' in request.form:
        task_item = request.form['input_text']
        print(task_item)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        sql_string_insert_task = '''
            INSERT INTO listitems(item, listnameid)
            VALUES('{}', (SELECT id FROM listnames
            WHERE listname = '{}' and userid =
            (SELECT id FROM users WHERE username = '{}')))
        '''.format(request.form['input_text'], session['chosenList'], session['username'])

        print(sql_string_insert_task)
        print(request.form['input_text'])
        print(session['username'])

        cursor.execute(sql_string_insert_task)
        conn.commit()
        return redirect(url_for('listitems'))
    return render_template('listitems.html')


@app.route('/index')
def go_to_index(): 
    return render_template('index.html')


# @app.route('/listslist')
# def get_lists_list(): 
#     cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
#     sql_string_insert_task = '''
#         SELECT listname FROM listnames
#         WHERE userid = 
#         (SELECT id 
#         FROM users 
#         WHERE username = '{}');
#     '''.format(session['username'])

#     print(sql_string_insert_task)
#     print(request.form['input_text'])
#     print(session['username'])
#     cursor.execute(sql_string_insert_task)
#     conn.commit()
#     resp = cursor.fetchall()
#     return render_template('listitems.html', lists_list=resp )





# ************************* PREDICTION

@app.route('/get_end_predictions', methods=['POST', 'GET'])
def get_prediction_result():
    print("predictions")
    try:
        input_text = ' '.join(request.json['input_text'].split())
        input_text += ' <mask>'
        top_k = 5
        res = wordpredict.get_predictions(input_text, top_clean=int(top_k))
        print(res)
        return app.response_class(response=json.dumps(res), status=200, mimetype='application/json')
    except Exception as error:
        err = str(error)
        print(err)
        return app.response_class(response=json.dumps(err), status=500, mimetype='application/json')




# @app.route('/listnames/get/')
# def do_function_get_user_list():
#     functions.get_user_list_names()
#     return


# @app.route('/profile')
# def profile():
#     return render_template('profile.html')
