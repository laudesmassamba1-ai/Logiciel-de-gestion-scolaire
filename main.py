from fastapi import FastAPI
import sqlite3

app = FastAPI()
conn = sqlite3.connect("ecole.db")