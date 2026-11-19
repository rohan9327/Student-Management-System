from database import get_db_connection

conn = get_db_connection()

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE Students (
    id INT PRIMARY KEY IDENTITY(1,1),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(15),
    course VARCHAR(100)
)
""")

conn.commit()

print("Students Table Created Successfully!")

conn.close()