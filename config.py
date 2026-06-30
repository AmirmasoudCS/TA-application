import os
BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__));
DB_PATH = os.path.join(BASE_DIRECTORY,"universityDB.db");
EXPORT_DIRECTORY = os.path.join(BASE_DIRECTORY,"exports");
LOG_DIRECTORY = os.path.join(BASE_DIRECTORY,'logs');
os.makedirs(EXPORT_DIRECTORY,exist_ok=True);
os.makedirs(LOG_DIRECTORY,exist_ok=True);