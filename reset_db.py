import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SLearn.settings')
django.setup()

print("Dropping public schema...")
with connection.cursor() as cursor:
    cursor.execute("DROP SCHEMA public CASCADE;")
    cursor.execute("CREATE SCHEMA public;")
print("Database schema cleared successfully.")
