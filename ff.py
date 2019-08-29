#!/usr/bin/env python

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
app = Flask(__name__)

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Job, Ability
app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "ff14"


engine = create_engine('sqlite:///ff14jobs.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/jobs/<int:job_id>/')
def restaurantMenu(job_id):
    login = 0
    if 'username' in login_session:
        login = 1
    job = session.query(Job).filter_by(id=job_id).one()
    items = session.query(Ability).filter_by(job_id=job.id)
    return render_template('class.html', job=job, items = items, login=login)


@app.route('/')
@app.route('/hello')
def HelloWorld():
    
    return render_template('index.html')

@app.route('/all')
def testhello():
    if 'username' not in login_session:
        return redirect('/login')
    job = session.query(Job).all()
    output = ''
    for i in job:
        output += i.name
        output += '</br>'
        output += '</br>'
        output += i.description
        output += '</br>'
        output += '</br>'
        output += '</br>'
    return output

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/healer')
def test1():
    login = 0
    if 'username' in login_session:
        login = 1
    job1 = session.query(Job).filter_by(role = 'Healer')
    return render_template('classes.html', job=job1, login=login)

@app.route('/tank')
def test2():
    login = 0
    if 'username' in login_session:
        login = 1
    job2 = session.query(Job).filter_by(role = 'Tank')
    return render_template('classes.html', job=job2, login=login)
   
@app.route('/dps')
def test3():
    login = 0
    if 'username' in login_session:
        login = 1
    job3 = session.query(Job).filter_by(role = 'Dps')
    return render_template('classes.html', job=job3, login=login)




@app.route('/jobs/<int:job_id>/delete',
           methods=['GET', 'POST'])
def deleteJob(job_id):
    jobToDelete = session.query(Job).filter_by(id=job_id).one()

    if request.method == 'POST':
        session.delete(jobToDelete)
        session.commit()
        return redirect('/')
    else:
        return render_template('delete.html', item=jobToDelete)

@app.route('/JSON')
def ffJSON():
    jobs = session.query(Job).all()
  
    return jsonify(ffItems=[i.serialize for i in jobs])

@app.route('/jobs/<int:job_id>/<int:ability_id>/edit',
           methods=['GET', 'POST'])
def editAbility(job_id, ability_id):
    editedAbility = session.query(Ability).filter_by(id=ability_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedAbility.name = request.form['name']
            editedAbility.level = request.form['level']
            editedAbility.description = request.form['description']
        session.add(editedAbility)
        session.commit()
        return redirect('/')
    else:
        return render_template(
            'edit.html', job_id=job_id, ability_id=ability_id, item=editedAbility)


@app.route('/jobs/<int:job_id>/new', methods=['GET', 'POST'])
def newAbility(job_id):

    if request.method == 'POST':
        newAbility = Ability(name=request.form['name'], description=request.form[
                           'description'], level=request.form['level'], Cast=request.form['Cast'], job_id=job_id)
        session.add(newAbility)
        session.commit()
        return redirect('/')
    else:
        return render_template('new.html', job_id=job_id)


if __name__ == '__main__':
    app.secret_key = 'ia1yTpinkCIgnkt_H8bHqswe'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)