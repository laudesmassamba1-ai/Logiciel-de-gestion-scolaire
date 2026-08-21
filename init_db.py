"""
Script d'initialisation de la base de données "ecole".
À lancer une seule fois sur chaque nouveau poste / nouvelle école,
avant de démarrer l'API pour la première fois.

Utilisation :
    python init_db.py
"""

import mysql.connector

HOST = "localhost"
USER = "root"
PASSWORD = "Josias50"
NOM_BASE = "ecole"
FICHIER_SCHEMA = "schema.sql"


def main():
    # Connexion SANS préciser de base, pour pouvoir la créer si elle n'existe pas
    conn = mysql.connector.connect(host=HOST, user=USER, password=PASSWORD)
    cursor = conn.cursor()

    # 1. Créer la base si elle n'existe pas déjà
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {NOM_BASE}")
    print(f"Base '{NOM_BASE}' prête.")
    cursor.execute(f"USE {NOM_BASE}")

    # 2. Lire le fichier schema.sql
    with open(FICHIER_SCHEMA, "r", encoding="utf-8") as f:
        script_sql = f.read()

    # 3. Exécuter chaque instruction CREATE TABLE une par une
    #    (on découpe sur les ";" et on ignore les lignes vides/commentaires)
    instructions = [req.strip() for req in script_sql.split(";") if req.strip()]

    tables_creees = 0
    for instruction in instructions:
        # On ignore les blocs qui ne contiennent que des commentaires
        lignes_utiles = [
            l for l in instruction.split("\n") if l.strip() and not l.strip().startswith("--")
        ]
        if not lignes_utiles:
            continue
        instruction_propre = "\n".join(lignes_utiles)
        try:
            cursor.execute(instruction_propre)
            tables_creees += 1
        except mysql.connector.Error as err:
            # Code 1050 = "Table already exists" -> pas grave, on continue
            if err.errno == 1050:
                print(f"  (déjà existante, ignorée)")
            else:
                print(f"Erreur sur une instruction : {err}")
                raise

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Terminé : {tables_creees} instruction(s) traitée(s).")
    print("La base de données est prête à être utilisée par l'API.")


if __name__ == "__main__":
    main()