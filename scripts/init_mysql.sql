-- Creation unique de la base MySQL de l'ecole + d'un utilisateur dedie.
-- A executer UNE SEULE FOIS, avec vos droits administrateur :
--
--    sudo mysql < scripts/init_mysql.sql
--
-- IMPORTANT : changez le mot de passe ci-dessous avant l'execution,
-- et reportez-le dans scripts/lancer_synchronise.sh (GS_DB_PASSWORD).

CREATE DATABASE IF NOT EXISTS ecole CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'gs_app'@'localhost' IDENTIFIED BY 'gs_motdepasse_a_changer';
GRANT ALL PRIVILEGES ON ecole.* TO 'gs_app'@'localhost';
FLUSH PRIVILEGES;
