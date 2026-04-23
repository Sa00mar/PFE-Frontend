import psycopg2

def get_connection():
    """
    Retourne une connexion PostgreSQL
    """
    return psycopg2.connect(
        host="localhost",          # Ton serveur PostgreSQL, ici en local
        database="pfe_testing_ia", # Nom de ta base
        user="postgres",           # Ton utilisateur PostgreSQL
        password="admin" # Ton mot de passe PostgreSQL
    )