import psycopg2
from config import Config

def apply_database_updates():
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=Config.SQLALCHEMY_DATABASE_URI.split('/')[-1].split('?')[0],
            user='postgres',
            password='Paradox',
            host='localhost',
            port='5432'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read the SQL file
        with open('database_updates.sql', 'r') as sql_file:
            sql_commands = sql_file.read()
        
        # Execute the SQL commands
        cursor.execute(sql_commands)
        print("Database updates applied successfully!")
        
    except Exception as e:
        print(f"Error applying database updates: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    apply_database_updates()
