import pyodbc

def get_db_connection():

    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=StudentManagementDB;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
    )

    return conn


# Activity Log Function
def add_log(username, action):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ActivityLogs (username, action, activity_date)
        VALUES (?, ?, GETDATE())
    """, (username, action))

    conn.commit()

    cursor.close()
    conn.close()
