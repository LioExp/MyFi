import sqlite3
from datetime import datetime 

# 1. Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect('data/myfi.db')
# 2. Create a cursor object to execute SQL commands
cursor = conn.cursor()

def init_db():
    # 3. Execute the SQL command to create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dispositivos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,    
            MAC TEXT,
            nome TEXT NOT NULL,
            IP TEXT NOT NULL,
            bytes_enviados INTEGER,
            bytes_recebidos INTEGER,
            timestamp TEXT
        )
    ''')
    # 4. Commit the changes and close the connection
    conn.commit()

def save_to_db(mac,nome,ip,bytes_enviados,bytes_recebidos):
    # gerar o timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 3. Insert a single row
    # Use '?' placeholders to prevent SQL injection
    cursor.execute("INSERT INTO dispositivos (mac,nome,ip,bytes_recebidos,bytes_enviados, timestamp) VALUES (?,?, ?, ?, ?, ?)", (mac, nome, ip, bytes_enviados, bytes_recebidos,timestamp))
    conn.commit()

if __name__ == '__main__':
    init_db()
    save_to_db('e4:18:6b:aa:39:eb', '_gateway', '192.168.1.1', 100, 200)
    print('Guardado com sucesso')