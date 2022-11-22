from flask import Flask, render_template,request,redirect,session 
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import random
import ibm_db
import re
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2
import json
import requests

userid = 'dhivya'
apikey = ''
appid = 'dhivya'
model = 'food-item-recognition'

hostname = ""
uid = ""
pwd = ""
database = ""
port = ""

app = Flask(__name__)

app.secret_key = "Dhivya"

conn = ibm_db.connect(f"DATABASE={database};HOSTNAME={hostname};PORT={port};SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID={uid};PWD={pwd};", "", "")

@app.route("/")
def main():
    return render_template("index.html")

@app.route("/dash")
def dash():
    return render_template("dash.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")
    
@app.route("/uploader", methods = ["POST","GET"])
def uploader():
    if request.method == "POST":
        f = request.files["file"]
        image = f.read()

        channel = ClarifaiChannel.get_grpc_channel()
        stub = service_pb2_grpc.V2Stub(channel)

        metadata = (('authorization', 'Key ' + apikey),)

        userDataObject = resources_pb2.UserAppIDSet(user_id=userid, app_id=appid)

        post_model_outputs_response = stub.PostModelOutputs(
            service_pb2.PostModelOutputsRequest(
                user_app_id=userDataObject,
                model_id=model, 
                inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(
                        image=resources_pb2.Image(
                            base64=image
                        )
                    )
                )      
            ]
            ),
            metadata=metadata
        )
        if post_model_outputs_response.status.code != status_code_pb2.SUCCESS:
            print(post_model_outputs_response.status)
            itemmsg = "Upload a valid image"
            return render_template("upload.html",itemmsg=itemmsg)
        
        output = post_model_outputs_response.outputs[0]

        item = output.data.concepts[0].name

        print(item)
        url = "https://food-nutrition-information.p.rapidapi.com/foods/search"

        querystring = {"query":f"{item}","pageSize":"1","pageNumber":"1"}

        headers = {
            "X-RapidAPI-Key": "",
            "X-RapidAPI-Host": "food-nutrition-information.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        r = response.text

        jsondata = json.loads(r)

        lst = []

        for i in range(len(jsondata['foods'][0]['foodNutrients'])):
            print(jsondata['foods'][0]['foodNutrients'][i]['nutrientName'])
            lst.append(jsondata['foods'][0]['foodNutrients'][i]['nutrientName'])

        print(lst)
        lstlen = len(lst)
        return render_template("value.html",item=item,lstlen=lstlen,lst=lst)
    itemmsg = "Upload a valid image"
    return render_template("upload.html",itemmsg=itemmsg)
    if __name__ == "__main__":
        app.run(use_reloader=True,debug=True)



@app.route("/about")
def about():
    return render_template("about.html")    

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/signinvalid",methods = ["POST","GET"])
def signinv():
    if request.method == "POST":
        global username
        global password
        username = request.form.get("usernamel")
        password = request.form.get("passwdl")
        msgl = ""
        stringl = ""
        sqll = "SELECT * FROM REGISTER WHERE USERNAME =? AND PASSWORD =?"
        stmtl = ibm_db.prepare(conn, sqll)
        ibm_db.bind_param(stmtl,1,username)
        ibm_db.bind_param(stmtl,2,password)
        ibm_db.execute(stmtl)
        accountl = ibm_db.fetch_assoc(stmtl)
        print(accountl)

        if accountl:
            session["username"] = accountl["USERNAME"]
            stringl = f"{username} login success"
            return render_template("dash.html",stringl=stringl)
        else:
            msgl = "Incorrect Username and Password"
    return render_template("signin.html",msgl=msgl)


@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signupvalid",methods = ["POST","GET"])
def signupv():
    if request.method == "POST":
        global mail
        global user
        global passwd
        mail = request.form.get("emailaddress")
        user = request.form.get("username")
        passwd = request.form.get("passwd")
        msg = ""
        userstatus = ""
        mailstatus = ""
        passwdstatus = ""

        sql = "SELECT * FROM REGISTER WHERE USERNAME =?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt,1,user)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)

        if account:
            msg = "Account already exists"
        elif not re.match(r'[A-Za-z0-9]+', user):
            userstatus = "Please enter valid username"
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', mail):
            mailstatus = "Please enter valid email"
        elif (passwd==""):
            passwdstatus = "Please enter valid password"
        else:
            sentotp(user,mail)
            return render_template("validate.html")
        return render_template("signup.html",mailstatus=mailstatus,userstatus=userstatus,passwdstatus=passwdstatus,msg=msg)

@app.route("/checkotp",methods = ["POST","GET"])
def checkotp():
    if request.method == "POST":
        rotp = request.form.get("otp")
        if (str(rotp)==str(sotp)):

            sql1="INSERT INTO REGISTER(USERNAME,PASSWORD,MAIL) VALUES(?,?,?)"
            stmt1 = ibm_db.prepare(conn, sql1)
            
            ibm_db.bind_param(stmt1,1,user)
            ibm_db.bind_param(stmt1,2,passwd)
            ibm_db.bind_param(stmt1,3,mail)
            ibm_db.execute(stmt1)

            result = "Account Created Succesfully"
            return render_template("result.html",result=result)
        else:
            status = "Please enter valid OTP"
            return render_template("validate.html",status=status)


def sentotp(user,mail):
    global sotp
    sotp = random.randint(1000,9999)
    message = Mail(
    from_email='dhivyavpy@gmail.com',
    to_emails=mail,
    subject='Otp verification',
    html_content=f'Hello {user} This is OTP - {sotp}')
    sg = SendGridAPIClient("")
    response = sg.send(message)


@app.route("/logout")
def logout():
    session.pop("username", None)
    return render_template("/index.html")    


if __name__ == "__main__":
    app.run(debug=True)