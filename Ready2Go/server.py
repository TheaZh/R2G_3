import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, session, redirect, Response


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# connect to database
DATABASEURI = "postgresql://qz2271:dwy32@104.196.175.120/postgres"  # URI
engine = create_engine(DATABASEURI)  # create a database engine


@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request
    The variable g is globally accessible
    """
    try:
        g.conn = engine.connect()
        # g.user = current_user
    except:
        print "uh oh, problem connecting to database"
        import traceback; traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


# Home page -- index.html
@app.route('/')
def index():
    """
    request is a special object that Flask provides to access web request information:

    request.method:   "GET" or "POST"
    request.form:     if the browser submitted a form, this contains the data in the form
    request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

    See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
    """

    return render_template('index.html')


@app.route('/home_login')
def home_login():
    return render_template('home_login.html', username=user)


# Log In
@app.route('/ShowSignIn')
def showsignin():
    return render_template('signIn.html')


#determine if the input is safe  -- contains no SQL.
def safe_input(inp):
    key=['drop','table','database','select','update',';','delete','<!--','insert','--','#']
    for x in key:
        if x in inp.lower():
            return False
        else:
            continue
    return True

#determine if the input contains space which is not allowed.
def no_space(inp):
    if not inp.find(' '):  # not contain space
        return True
    return False


@app.route('/signIn', methods=['POST'])
def signin():
    username = request.form['username']
    password = request.form['password']
    if not safe_input(username) or not safe_input(password):
        return render_template('signIn.html', SignIn_error='No SQL. Please try again!')
    cmd = 'SELECT password,u_id FROM Clients WHERE name=(:username1)';
    cursor = g.conn.execute(text(cmd), username1=username);
    isexisted = cursor.rowcount # the user does not exist
    result=[]
    for i in cursor.first():
        result.append(i)
    psword = result[0]
    cursor.close()
    if isexisted == 0:
        return render_template('signIn.html', SignIn_error='The user does not exist. Please try again!')
    elif psword == password: # is password correct?
        global user
        user = username # current user's username
        # correct
        global info_uid
        info_uid= result[1]
        return redirect('/home_login')
    else:
        # wrong --  load signIn.html again, and show the error information
        return render_template('signIn.html', SignIn_error='Your username or password is incorrect. Please try again!')


# Log out
@app.route('/logout')
def logout():
    return redirect('/')


# Sign up
@app.route('/ShowSignUp')
def showsignup():
    return render_template('signUp.html')


@app.route('/signUp', methods=['POST'])
def signup():
    new_username = request.form['username']
    new_password = request.form['password']
    # insert new client's information into table clients. if the s username does not exist.
    if not safe_input(new_username) or not safe_input(new_password):
        return render_template('signUp.html', SignUp_error='No SQL. Please try again!')
    cmd0 = 'SELECT * FROM clients WHERE name=(:new_username)'
    cur = g.conn.execute(text(cmd0), new_username=new_username)
    count = cur.rowcount  # is there the same username in database?
    cur.close()
    # count the new u_id
    cmd1 = 'SELECT * FROM clients'
    cursor = g.conn.execute(text(cmd1))
    count0=cursor.rowcount
    cursor.close()
    uid = count0 + 10100 # new_uid number
    global info_uid
    info_uid=uid
    if count == 0:
        if no_space(new_username) and no_space(new_password):
            # there is no same record in table clients
            cmd = 'INSERT INTO clients(u_id,name,password) VALUES ((:new_uid),(:new_username),(:new_password))';
            g.conn.execute(text(cmd), new_uid=uid, new_username=new_username, new_password=new_password);
            global user
            user=new_username
            return redirect('/home_login')
        else:
            return render_template('signUp.html', SignUp_error='No space allowed. Please try again')
    else:
        # the username has already in the table clients
        return render_template('signUp.html', SignUp_error='The username has already existed. Please try a new one.')


@app.route('/history')
def history():
    cmd = '''SELECT t.name as group_name,t.start_date as group_start_date,o.date as order_date
             FROM TravelGroups t,orders o,clients c
             WHERE o.tg_id=t.tg_id and c.u_id=o.u_id and c.u_id=(:uid)'''
    cur = g.conn.execute(text(cmd),uid=info_uid)
    num = cur.rowcount  # the number of records
    row = []
    for i in range(num):
        row.append(cur.fetchone()) # put every record into the list
    return render_template('history.html', record=row, num=num)


@app.route('/addHistory')
def addhistory():
    try:
        groupname = request.args.get('groupname')
        cmd = 'SELECT tg_id FROM TravelGroups WHERE name = (:name1)'
        cur = g.conn.execute(text(cmd), name1=groupname)
        group = []
        group.append(cur.fetchone())
        cur.close()
        groupid = group[0][0]
        cmd = '''INSERT INTO orders VALUES (:u_id,:tg_id,now())'''
        g.conn.execute(text(cmd), u_id=info_uid, tg_id=groupid)
        return redirect('/history')
    except:
        return render_template('addHistoryError.html',groupname=groupname)


@app.route('/addHistoryError')
def addhistoryerror():
    return render_template('addHistoryError.html')


@app.route('/favorite')
def favorite():
    cmd = '''SELECT t.name as group_name
             FROM likes l,clients c,travelgroups t
             WHERE l.u_id=c.u_id and l.tg_id=t.tg_id and c.u_id=(:uid)'''
    cur = g.conn.execute(text(cmd), uid=info_uid)
    num = cur.rowcount  # the number of records
    row = []
    for i in range(num):
        row.append(cur.fetchone()) # put every record into the list
    return render_template('favorite.html', record=row, num=num)


@app.route('/addFavorite')
def addfavorite():
    try:
        groupname = request.args.get('groupname')
        cmd = 'SELECT tg_id FROM TravelGroups WHERE name = (:name1)'
        cur = g.conn.execute(text(cmd), name1=groupname)
        group = []
        group.append(cur.fetchone())
        cur.close()
        groupid = group[0][0]
        cmd = '''INSERT INTO likes VALUES (:u_id,:tg_id)'''
        g.conn.execute(text(cmd), u_id=info_uid, tg_id=groupid)
        return redirect('/favorite')
    except:
        return render_template('addFavoriteError.html',groupname=groupname)


@app.route('/addFavoriteError')
def addfavoriteerror():
    return render_template('addFavoriteError.html')


@app.route('/personInfo')
def personinfo():
    cmd = 'SELECT name,gender,phone,preference FROM clients WHERE u_id=(:uid)'
    cur = g.conn.execute(text(cmd),uid=info_uid)
    info=[]
    for i in cur.first():
        info.append(i)
    cur.close()
    return render_template('personInfo.html', username=info[0], uid=info_uid, gender=info[1], phone=info[2],
                           preference=info[3])


@app.route('/ShowManageInfo')
def showmanageinfo():
    cmd = 'SELECT name,gender,phone,preference FROM clients WHERE u_id=(:uid)'
    cur = g.conn.execute(text(cmd), uid=info_uid)
    info = []
    for i in cur.first():
        info.append(i)
    cur.close()
    manage_error = ''
    return render_template('manageInfo.html', username=info[0], uid=info_uid, gender=info[1],
                           preference=info[3], phone=info[2],Manage_error=manage_error)


@app.route('/ManageInfo', methods=["POST"])
def manageinfo():
    # global uid --> info_uid
    update_username = request.form['username']
    # update_password = request.form['password']
    update_gender = request.form['gender']
    update_phone = request.form['phone']
    update_preference = request.form['preference']
    uid = info_uid  # cannot change u_id
    if not safe_input(update_username) or not safe_input(update_phone):
        manage_error ='No SQL. Please try again!'
        cmd = 'SELECT name,gender,phone,preference FROM clients WHERE u_id=(:uid)'
        cur = g.conn.execute(text(cmd), uid=info_uid)
        info = []
        for i in cur.first():
            info.append(i)
        cur.close()
        return render_template('manageInfo.html', username=info[0], uid=info_uid, gender=info[1],
                               preference=info[3], phone=info[2], Manage_error=manage_error)
    if no_space(update_username) and no_space(update_phone):
        cmd='UPDATE clients set name=(:username),gender=(:gender),phone=(:phone),preference=(:pre) WHERE u_id=(:uid)'
        g.conn.execute(text(cmd), username=update_username, gender=update_gender, phone=update_phone,
                       pre=update_preference, uid=uid)
        return redirect('/personInfo')
    else:
        manage_error = 'No space allowed. Please try again!'
        cmd = 'SELECT name,gender,phone,preference FROM clients WHERE u_id=(:uid)'
        cur = g.conn.execute(text(cmd), uid=info_uid)
        info = []
        for i in cur.first():
            info.append(i)
        cur.close()
        return render_template('manageInfo.html', username=info[0], uid=info_uid, gender=info[1],
                               preference=info[3], phone=info[2], Manage_error=manage_error)


@app.route('/Showsearch')
def showsearch():
    return render_template('search.html')

@app.route('/Showsearch_login')
def showsearch_login():
    return render_template('search_login.html',username=user)

@app.route('/Showsearchscenic_login')
def showsearchscenic_login():
    return render_template('searchscenic_login.html',username=user)

@app.route('/Showsearchscenic')
def showsearchscenic():
    return render_template('searchscenic.html')

@app.route('/searchscenic',methods=["POST"])
def searchscenic():
    scenic = request.form['scenic']
    if not safe_input(scenic):
        return render_template('searchscenic.html', error='No SQL. Please try again!')
    name='%'+ scenic.strip() +'%'
    cmd = 'SELECT name FROM ScenicSpots WHERE lower(name) like lower(:name1)'
    cur = g.conn.execute(text(cmd), name1=name)
    num=cur.rowcount
    info = []
    for i in range(num):
        info.append(cur.fetchone())
    cur.close()
    return render_template('searchscenic.html',record=info,number=num)

@app.route('/searchscenic_login',methods=["POST"])
def searchscenic_login():
    scenic = request.form['scenic']
    if not safe_input(scenic):
        return render_template('searchscenic_login.html', error='No SQL. Please try again!')
    name='%'+ scenic.strip() +'%'
    cmd = 'SELECT name FROM ScenicSpots WHERE lower(name) like lower(:name1)'
    cur = g.conn.execute(text(cmd), name1=name)
    num=cur.rowcount
    info = []
    for i in range(num):
        info.append(cur.fetchone())
    cur.close()
    return render_template('searchscenic_login.html',record=info,number=num,username=user)


@app.route('/search',methods=["POST"])
def search():
    searchgroup = request.form['searchgroup']
    if not safe_input(searchgroup):
        return render_template('search.html', error='No SQL. Please try again!')
    name='%'+ searchgroup.strip() +'%'
    cmd = 'SELECT name FROM TravelGroups WHERE lower(name) like lower(:name1)'
    cur = g.conn.execute(text(cmd), name1=name)
    num=cur.rowcount
    info = []
    for i in range(num):
        info.append(cur.fetchone())
    cur.close()
    return render_template('search.html',record=info,number=num)

@app.route('/search_login',methods=["POST"])
def search_login():
    searchgroup = request.form['searchgroup']
    if not safe_input(searchgroup):
        return render_template('search_login.html', error='No SQL. Please try again!')
    name='%'+ searchgroup.strip() +'%'
    cmd = 'SELECT name FROM TravelGroups WHERE lower(name) like lower(:name1)'
    cur = g.conn.execute(text(cmd), name1=name)
    num=cur.rowcount
    info = []
    for i in range(num):
        info.append(cur.fetchone())
    cur.close()
    return render_template('search_login.html',record=info,number=num,username=user)



@app.route('/result')
def result():
    groupname=request.args.get('groupname')
    cmd='SELECT * FROM TravelGroups WHERE name = :name1'
    cur = g.conn.execute(text(cmd), name1=groupname)
    group = []
    for i in cur.first():
        group.append(i)
    cur.close()
    tg_id=group[0]
    guide_id=group[6]
    r_id=group[7]
    cmd = 'SELECT * FROM TravelRoutes_Contain WHERE r_id=:name1'
    cur = g.conn.execute(text(cmd), name1=r_id)
    route = []
    for i in cur.first():
        route.append(i)
    cur.close()
    cmd='SELECT * FROM Contain WHERE r_id=:name1 order by day'
    cur = g.conn.execute(text(cmd), name1=r_id)
    routesc = []
    num = cur.rowcount
    for i in range(num):
        routesc.append(cur.fetchone())
    cur.close()
    cmd='SELECT * FROM LiveIn as l,Hotels as h WHERE l.tg_id=:name1 and l.h_id=h.h_id'
    cur = g.conn.execute(text(cmd), name1=tg_id)
    hotel = []
    num = cur.rowcount
    for i in range(num):
        hotel.append(cur.fetchone())
    cur.close()
    cmd='SELECT * FROM Transportation as t,Take as a WHERE a.tg_id=:name1 and t.tr_id=a.tr_id'
    cur = g.conn.execute(text(cmd), name1=tg_id)
    trans = []
    num = cur.rowcount
    for i in range(num):
        trans.append(cur.fetchone())
    cur.close()
    cmd='SELECT u_id,name FROM Guides WHERE u_id=:name1'
    cur = g.conn.execute(text(cmd), name1=guide_id)
    guides = []
    for i in cur.first():
        guides.append(i)
    cur.close()
    return render_template('result.html',group=group,route=route,routesc=routesc,hotel=hotel,trans=trans,guides=guides)

@app.route('/result_login')
def result_login():
    groupname=request.args.get('groupname')
    cmd='SELECT * FROM TravelGroups WHERE name = :name1'
    cur = g.conn.execute(text(cmd), name1=groupname)
    group = []
    for i in cur.first():
        group.append(i)
    cur.close()
    tg_id=group[0]
    guide_id=group[6]
    r_id=group[7]
    cmd = 'SELECT * FROM TravelRoutes_Contain WHERE r_id=:name1'
    cur = g.conn.execute(text(cmd), name1=r_id)
    route = []
    for i in cur.first():
        route.append(i)
    cur.close()
    cmd='SELECT * FROM Contain WHERE r_id=:name1 order by day'
    cur = g.conn.execute(text(cmd), name1=r_id)
    routesc = []
    num = cur.rowcount
    for i in range(num):
        routesc.append(cur.fetchone())
    cur.close()
    cmd='SELECT * FROM LiveIn as l,Hotels as h WHERE l.tg_id=:name1 and l.h_id=h.h_id'
    cur = g.conn.execute(text(cmd), name1=tg_id)
    hotel = []
    num = cur.rowcount
    for i in range(num):
        hotel.append(cur.fetchone())
    cur.close()
    cmd='SELECT * FROM Transportation as t,Take as a WHERE a.tg_id=:name1 and t.tr_id=a.tr_id'
    cur = g.conn.execute(text(cmd), name1=tg_id)
    trans = []
    num = cur.rowcount
    for i in range(num):
        trans.append(cur.fetchone())
    cur.close()
    cmd='SELECT u_id,name FROM Guides WHERE u_id=:name1'
    cur = g.conn.execute(text(cmd), name1=guide_id)
    guides = []
    for i in cur.first():
        guides.append(i)
    cur.close()
    return render_template('result_login.html',group=group,route=route,routesc=routesc,hotel=hotel,trans=trans,guides=guides,username=user)

@app.route('/scenic')
def scenic():
    name=request.args.get('scenicname')
    cmd='SELECT s.*,t.name  FROM Contain as c, ScenicSpots as s,TravelGroups as t WHERE c.name=:name1 and c.r_id=t.r_id and c.name=s.name'
    cur = g.conn.execute(text(cmd), name1=name)
    scenic = []
    num = cur.rowcount
    for i in range(num):
        scenic.append(cur.fetchone())
    cur.close()
    return render_template('scenic.html',scenic=scenic)

@app.route('/scenic_login')
def scenic_login():
    name=request.args.get('scenicname')
    cmd='SELECT s.*,t.name  FROM Contain as c, ScenicSpots as s,TravelGroups as t WHERE c.name=:name1 and c.r_id=t.r_id and c.name=s.name'
    cur = g.conn.execute(text(cmd), name1=name)
    scenic = []
    num = cur.rowcount
    for i in range(num):
        scenic.append(cur.fetchone())
    cur.close()
    return render_template('scenic_login.html',scenic=scenic,username=user)

@app.route('/guideinfo_login')
def guideinfo_login():
    guide_id = request.args.get('guide_id')
    cmd = 'SELECT * FROM Guides as g,TravelAgencies as ta WHERE g.u_id=:name1 and g.agency = ta.name'
    cur = g.conn.execute(text(cmd), name1=guide_id)
    guides = []
    for i in cur.first():
        guides.append(i)
    cur.close()
    return render_template('guides_login.html',guides=guides,username=user)

@app.route('/guideinfo')
def guideinfo():
    guide_id = request.args.get('guide_id')
    cmd = 'SELECT * FROM Guides as g,TravelAgencies as ta WHERE g.u_id=:name1 and g.agency = ta.name'
    cur = g.conn.execute(text(cmd), name1=guide_id)
    guides = []
    for i in cur.first():
        guides.append(i)
    cur.close()
    return render_template('guides.html',guides=guides)

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):

        HOST, PORT = host, port
        print "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
    run()
