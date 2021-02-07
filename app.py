import sqlite3
import os
import datetime
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, request, url_for, render_template, redirect, session

currentDirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

app.secret_key = "Hspt"

color = datetime.now().hour


@app.route('/init', methods=["GET", "POST"])
def init():
    if request.method == "GET":
        return render_template("init.html")
    if request.method == "POST":
        password = request.form.get("pass")
        if password == "SBS STUDENT!":
            # initialize the DataBase
            # initialize users.db
            connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS users (userName TEXT, passWord TEXT, PointsGiven INTEGER)")
            cursor.execute("CREATE TABLE IF NOT EXISTS housePoints (house TEXT, points INTEGER, latest_update TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS history (person TEXT, reason TEXT, date DATE, house TEXT, points INTEGER, givenBy TEXT)")
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS individual (person TEXT, points INTEGER, latest TEXT, house TEXT)")
            cursor.execute("INSERT INTO housePoints(house, points, latest_update) VALUES ('Water', 0, '')")
            cursor.execute("INSERT INTO housePoints(house, points, latest_update) VALUES ('Wind', 0, '')")
            cursor.execute("INSERT INTO housePoints(house, points, latest_update) VALUES ('Fire', 0, '')")
            cursor.execute("INSERT INTO housePoints(house, points, latest_update) VALUES ('Earth', 0, '')")
            connection.commit()
            return redirect("/")


@app.route('/display', methods=["GET"])
def display():
    connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
    cursor = connection.cursor()
    result = cursor.execute("SELECT * FROM housePoints")
    houses = result.fetchall()
    histories = cursor.execute("SELECT * FROM history ORDER BY date DESC LIMIT 80")
    histories = histories.fetchall()
    first = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 1")
    first = first.fetchall()[0][0]
    second = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 2")
    second = second.fetchall()[1][0]
    third = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 3")
    third = third.fetchall()[2][0]
    fourth = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 4")
    fourth = fourth.fetchall()[3][0]
    p1 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 1")
    p1 = p1.fetchall()[0][0]
    p2 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 2")
    p2 = p2.fetchall()[1][0]
    p3 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 3")
    p3 = p3.fetchall()[2][0]
    p4 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 4")
    p4 = p4.fetchall()[3][0]

    data_folder = currentDirectory
    announcementf = open(currentDirectory + "/static/announcement.txt", "r")
    announcement = announcementf.read()
    return render_template("display.html", announcements=announcement, houses=houses, histories=histories, first=first, second=second, third=third, fourth=fourth, p1=p1, p2=p2, p3=p3, p4=p4)


@app.route('/old', methods=["GET", "POST"])
def index():
    if "user" in session:
        # if user in session, display the user id
        if request.method == "GET":
            # if user in session, display the user id
            students = ["A", "B", "C", "D"]
            return render_template('index.html', result=session["user"], students=students)
        if request.method == "POST":
            # handling of house, points, reason, and student name.
            if request.form["button"] == "enter":
                house = request.form.get('house')
                house = house.lower().capitalize()
                availableHouses = ['wind', 'water', 'earth', 'fire']
                # Check if house is inputted correctly
                if not availableHouses.__contains__(house.lower()):
                    return "Error, House doesn't exist, type water, wind, earth or fire."
                else:
                    points = request.form.get('points')
                    reason = request.form.get('reason')
                    studentName = request.form.get('studentName')
                    studentName = studentName.lower().title()
                    addStudent = request.form.get('addStudent')
                    connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
                    cursor = connection.cursor()
                    # Check if student name exist
                    studentCheckQuery = "SELECT person FROM individual WHERE person = '{}'".format(studentName)
                    houseCheckQuery = "SELECT house FROM individual WHERE person = '{}'".format(studentName)
                    houseOfStudent = cursor.execute(houseCheckQuery)
                    studentWithName = cursor.execute(studentCheckQuery)
                    studentWithName = studentWithName.fetchall()
                    studentExists = (studentWithName != [])
                    if (studentExists is False and (addStudent is None)):
                        # Ask to add student
                        return "ERROR - There's no student with this name, go back and check the 'I want to create a student' checkbox if you wish to create this student. Make sure you have typed the student in like Englishname Lastname - Example: Zack Xu"
                    if addStudent is not None:
                        print("1")
                        addStudentQuery = "INSERT INTO individual (person, points, latest, house) VALUES ('{}', {}, '{}', '{}')".format(
                            studentName, points, reason, house)
                        cursor.execute(addStudentQuery)
                        connection.commit()
                    if len(studentWithName) > 1:
                        print("2")
                        return "Problem - More than one student have that name, please report to admin."
                    if len(studentWithName) == 1:
                        houseOfStudent = houseOfStudent.fetchall()[0][0]
                        if houseOfStudent != house:
                            return "ERROR - Are you sure you put the right house? If you are sure about that, please report this error to admin."
                        print("3")
                        originalPointsQuery = "SELECT points FROM individual WHERE person = '{}'".format(studentName)
                        stPoints = cursor.execute(originalPointsQuery)
                        stPoints = stPoints.fetchall()[0][0]
                        stPoints = int(points) + int(stPoints)

                        updateStudentQuery = "UPDATE individual SET points = {}, latest = '{}' WHERE person = '{}'".format(
                            stPoints, reason, studentName)
                        print(updateStudentQuery)
                        cursor.execute(updateStudentQuery)
                        connection.commit()
                    # Get the current points of the house
                    query1 = "SELECT points FROM housePoints WHERE house = '{}'".format(house)
                    existingPointsquery = cursor.execute(query1)
                    existingPoints = existingPointsquery.fetchall()[0][0]
                    # Get points + new points
                    finalPoints = int(existingPoints) + int(points)
                    time.sleep(0.5)
                    connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
                    cursor = connection.cursor()
                    update = studentName + " gained points because - " + reason
                    writeCmd = "REPLACE INTO housePoints (house, points, reason) VALUES ('{}' '{}' '{}')".format(house,
                                                                                                                 finalPoints,
                                                                                                                 update)
                    writePointsCmd = "UPDATE housePoints SET points = {}, latest_update = '{}' WHERE house = '{}'".format(
                        finalPoints, update, house)
                    cursor.execute(writePointsCmd)

                    connection.commit()
                    return render_template("index.html", message='Updated Database', result=session['user'])

            if request.form["button"] == "logout":
                session.clear()
                return redirect(url_for("login"))
    else:
        return redirect(url_for("signup"))


@app.route('/', methods=["GET", "POST"])
def teacher():
    if "user" in session:
        if request.method == "GET":

            connection = sqlite3.connect(currentDirectory + "/Students.db")
            cursor = connection.cursor()
            getStudentListQuery = "SELECT * FROM studentsList"
            students = cursor.execute(getStudentListQuery)
            students = students.fetchall()
            studentsFinal = []
            for student in students:
                studentsFinal.append(student[0] + " " + student[1] + " " + student[2])

            return render_template("teacher.html", students=studentsFinal, result=session["user"])
        if request.method == "POST":
            if request.form["button"] == "enter":
                points = request.form.get('points')
                if (int(points) > 5) or (int(points) < 1):
                    return "Error, you can't give more than 5 points or less than 1 point, hit back button and change it"
                reason = request.form.get('reason')
                studentNames = request.form["selectedStudents"]
                students = studentNames.split(", ")

                for studentName in students:
                    for _ in range(2):
                        # CODE FROM ONLINE #
                        string = studentName
                        # split string
                        spl_string = string.split()
                        # remove the last item in list
                        rm = spl_string[:-1]
                        # convert list to string
                        studentName = ' '.join([str(elem) for elem in rm])
                        # CODE FROM ONLINE #
                    print(studentName)
                    HPConnection = sqlite3.connect(currentDirectory + "/HousePoints.db")
                    HPcursor = HPConnection.cursor()
                    STConnection = sqlite3.connect(currentDirectory + "/Students.db")
                    STcursor = sqlite3.connect(currentDirectory + "/Students.db")
                    # Get house of student through SQLITE:
                    getHouseQuery = "SELECT house From studentsList WHERE studentName = '{}'".format(studentName)
                    house = STcursor.execute(getHouseQuery)
                    house = house.fetchall()[0][0]
                    # Get the current points of the house
                    query1 = "SELECT points FROM housePoints WHERE house = '{}'".format(house)
                    existingPointsquery = HPcursor.execute(query1)
                    existingPoints = existingPointsquery.fetchall()[0][0]
                    # Get points + new points
                    finalPoints = int(existingPoints) + int(points)
                    update = studentName + " gained points - " + reason
                    writePointsCmd = "UPDATE housePoints SET points = {}, latest_update = '{}' WHERE house = '{}'".format(
                        finalPoints, update, house)
                    HPcursor.execute(writePointsCmd)
                    existingTeacherPointsQ = "SELECT PointsGiven FROM users WHERE userName = '{}'".format(session["user"])
                    existingTeacherPoints = HPcursor.execute(existingTeacherPointsQ)
                    existingTeacherPoints = existingTeacherPoints.fetchall()[0][0]
                    finalTeacherPoints = int(existingTeacherPoints) + int(points)

                    writeTeacherCmd = "UPDATE users SET PointsGiven = {} WHERE userName = '{}'".format(
                        finalTeacherPoints, session["user"])
                    HPcursor.execute(writeTeacherCmd)


                    # Insert into history

                    adjustedDate = datetime.utcnow()
                    hours_added = timedelta(hours=8)
                    adjustedDate = adjustedDate + hours_added
                    historyCmd = "INSERT INTO history (person, reason, date, house, points, givenBy) VALUES ('{}', '{}', '{}', '{}', '{}', '{}')".format(
                        studentName, reason, adjustedDate, house, int(points), session['user'])
                    HPcursor.execute(historyCmd)
                    HPConnection.commit()

                    # Get Student:

                    connection = sqlite3.connect(currentDirectory + "/Students.db")
                    cursor = connection.cursor()
                    getStudentListQuery = "SELECT * FROM studentsList"
                    students = cursor.execute(getStudentListQuery)
                    students = students.fetchall()
                    studentsFinal = []
                    for student in students:
                        studentsFinal.append(student[0] + " " + student[1] + " " + student[2])
                return render_template("teacher.html", message='Result successfully logged', result=session['user'], students=studentsFinal)
            if request.form["button"] == "logout":
                session.clear()
                return redirect(url_for("login"))
    else:
        connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
        cursor = connection.cursor()
        result = cursor.execute("SELECT * FROM housePoints")
        houses = result.fetchall()
        histories = cursor.execute("SELECT * FROM history ORDER BY date DESC LIMIT 20")
        histories = histories.fetchall()
        first = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 1")
        first = first.fetchall()[0][0]
        second = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 2")
        second = second.fetchall()[1][0]
        third = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 3")
        third = third.fetchall()[2][0]
        fourth = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 4")
        fourth = fourth.fetchall()[3][0]
        p1 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 1")
        p1 = p1.fetchall()[0][0]
        p2 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 2")
        p2 = p2.fetchall()[1][0]
        p3 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 3")
        p3 = p3.fetchall()[2][0]
        p4 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 4")
        p4 = p4.fetchall()[3][0]

        data_folder = currentDirectory
        announcementf = open(currentDirectory + "/static/announcement.txt", "r")
        announcement = announcementf.read()
        return render_template("display.html", announcements=announcement, message="You are not signed in. If you are a teacher, sign up or sign in to give points", houses=houses, histories=histories, first=first, second=second, third=third, fourth=fourth, p1=p1, p2=p2, p3=p3, p4=p4)


@app.route('/manage', methods=["GET", "POST"])
def manage():
    if request.method == "GET":
        return render_template("manage.html")
    if request.method == "POST":
        password = request.form.get('adminPass')
        query = request.form.get('query')
        if password == "sqlitequery":
            connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
            cursor = connection.cursor()
            with connection:
                cursor.execute(query)
            return 'success'
        if password == "announce":
            fa = open(currentDirectory + "/static/announcement.txt", "w")
            fa.write(query)
            fa.close()
            return "Updated Announcement"
        if password == "a":
            f = open(currentDirectory + "/static/announce.txt", "w")
            f.write(query)
            f.close()
        if password == "a":
            f = open(currentDirectory + "/static/announce.txt", "w")
            f.write(query)
            f.close()


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template('signup.html')
    if request.method == "POST":
        key = request.form.get('key')
        if key == 'housepoints-2021':
            username = request.form.get('username')
            password = request.form.get('password')
            connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
            cursor = connection.cursor()

            # Check if previous accounts exists
            result = cursor.execute("SELECT COUNT(*) FROM users WHERE userName = ?", (username,))
            result = result.fetchall()[0][0]

            if result != 0:
                return "Error - User Exists"
            else:
                cursor.execute("INSERT INTO users (userName, passWord, PointsGiven) VALUES (?, ?, 0)", (username, password))
                connection.commit()
                return redirect(url_for("login"))
        else:
            return render_template("signup.html", message="Wrong Key! Are you a student?")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.permanent = True
    if request.method == "GET":
        return render_template("signin.html", message='')
    if request.method == "POST":
        try:
            print("H")
            username = request.form.get('username')
            password = request.form.get('password')
            connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
            cursor = connection.cursor()
            realPassword = cursor.execute("SELECT passWord FROM users WHERE userName = ?", (username,))
            realPassword = realPassword.fetchall()[0][0]
            print(realPassword)
            if password == realPassword:
                session["user"] = username;
                return redirect(url_for("teacher"))
        except:
            return render_template("signin.html", message="User doesn't exist")
        else:
            return redirect(url_for("login"))


@app.route("/stManage", methods=["GET", "POST"])
def stManage():
    if request.method == "GET":
        return render_template("studentManagement.html")
    if request.method == "POST":
        password = request.form.get('password')
        if password == "AddStudent":
            name = request.form.get('name')
            house = request.form.get('house')
            grade = request.form.get('grade')
            connection = sqlite3.connect(currentDirectory + "/Students.db")
            cursor = connection.cursor()
            addStudentQuery = "INSERT INTO studentsList (studentName, house, grade) VALUES ('{}', '{}', '{}')".format(name, house, grade)
            cursor.execute(addStudentQuery)
            connection.commit()
            return "DONE!"

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/flippingDisplay")
def flippingDisplay():
    connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
    cursor = connection.cursor()
    result = cursor.execute("SELECT * FROM housePoints")
    houses = result.fetchall()
    histories = cursor.execute("SELECT * FROM history ORDER BY date DESC LIMIT 20")
    histories = histories.fetchall()
    first = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 1")
    first = first.fetchall()[0][0]
    second = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 2")
    second = second.fetchall()[1][0]
    third = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 3")
    third = third.fetchall()[2][0]
    fourth = cursor.execute("SELECT house FROM housePoints ORDER BY points DESC LIMIT 4")
    fourth = fourth.fetchall()[3][0]
    p1 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 1")
    p1 = p1.fetchall()[0][0]
    p2 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 2")
    p2 = p2.fetchall()[1][0]
    p3 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 3")
    p3 = p3.fetchall()[2][0]
    p4 = cursor.execute("SELECT points FROM housePoints ORDER BY points DESC LIMIT 4")
    p4 = p4.fetchall()[3][0]

    data_folder = currentDirectory

    announcementf = open(currentDirectory + "/static/announcement.txt", "r")
    announcement = announcementf.read()

    announcef = open(currentDirectory + "/static/announce.txt", "r")
    announce = announcef.read()

    return render_template("flipDisplay.html", announce=announce, announcements=announcement, houses=houses, histories=histories, first=first, second=second, third=third, fourth=fourth, p1=p1, p2=p2, p3=p3, p4=p4)

@app.route("/Tree!")
def Tree():
    connection = sqlite3.connect(currentDirectory + "/HousePoints.db")
    cursor = connection.cursor()
    houses = ['Fire', 'Water', 'Wind', 'Earth']
    finalList = []
    for i in houses:
        query = "SELECT points FROM housePoints WHERE house = '{}'".format(i)
        result = cursor.execute(query)
        finalList.append(result.fetchall()[0][0])
    return str(finalList)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
