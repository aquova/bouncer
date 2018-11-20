# Calculates statistics and generates plots

import sqlite3

def genData():
    sqlconn = sqlite3.connect('sdv.db')
    data = sqlconn.execute("SELECT * FROM badeggs;").selectAll()
    sqlconn.close()

