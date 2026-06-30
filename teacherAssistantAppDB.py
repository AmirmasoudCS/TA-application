import sqlite3
import os
import sys
database_directory = "C:\\Users\\Hamegani ost\\Desktop\\Projects\\TAapp"
class Database:
    def __init__(self,dbName):
        fullPath = os.path.join(database_directory,dbName);
        self.con = sqlite3.connect(fullPath);
        self.cursor = self.con.cursor();
    def resetDB(self,tableName):
        query = f"DROP TABLE IF EXISTS '{tableName}'";
        self.cursor.execute(query);
        self.con.commit()
    def createStudentsTable(self,tableName):
        query = f"CREATE TABLE IF NOT EXISTS '{tableName}'(Sid INTEGER PRIMARY KEY,SName TEXT)"
        self.cursor.execute(query);
        self.con.commit();
    def populateStudents(self,studentsFilename,tableName):
        fullPath = os.path.join(database_directory,studentsFilename);
        with open(fullPath,'r',encoding='utf-8') as f:
            queryTemplate = f'INSERT OR IGNORE INTO "{tableName}"(SName,Sid) VALUES(?,?)'
            studentsToInsert=[];
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2 :
                    studentNameList= parts[:-1];
                    studentName = ' '.join(studentNameList)
                    studentID = int(parts[-1]);
                    studentsToInsert.append((studentName,studentID))
                else:
                    print(f"Skipping malformed line: {line.strip()}");
            if studentsToInsert:
                self.cursor.executemany(queryTemplate,studentsToInsert);
                self.con.commit();
                print(f"Successfully inserted {len(studentsToInsert)} students into '{tableName}' .")
            else:
                print("No valid student data found to insert.");
    def createTable(self,tableName,studentsFilename,courseName,baseGrade=None):
        self.cursor.execute("PRAGMA foreign_keys = ON;");
        finalTable = courseName+tableName;
        if tableName.endswith("Students"):
            query = f"CREATE TABLE IF NOT EXISTS '{finalTable}'(Sid INTEGER PRIMARY KEY,SName TEXT)";
            self.cursor.execute(query);
            self.con.commit()
            return;
        query = f"CREATE TABLE IF NOT EXISTS '{finalTable}'(Sid INTEGER PRIMARY KEY,Score INTEGER,Comment TEXT,FOREIGN KEY(Sid) REFERENCES '{courseName}Students'(Sid) ON DELETE CASCADE ON UPDATE CASCADE)"
        self.cursor.execute(query)
        self.con.commit()
        self.createAssessmentInfoTable(courseName)
        infoTable=f"{courseName}AssessmentInfo"
        createInfo =f"CREATE TABLE IF NOT EXISTS '{infoTable}'(tableName TEXT PRIMARY KEY,baseGrade INTEGER)"
        self.cursor.execute(createInfo)
        insertQuery=f"INSERT OR REPLACE INTO '{infoTable}'(tableName,baseGrade) VALUES(?,?)"
        self.cursor.execute(insertQuery,(finalTable,baseGrade))
        self.con.commit()
    def tableExists(self,tableName,courseName):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name =?",(courseName+tableName,))
        return self.cursor.fetchone() is not None
    def addItem(self,tableName,sid,score,comment=None):
        if comment == "":
            comment = "-";
        query = f"INSERT OR REPLACE INTO '{tableName}'(Sid,Score,Comment) VALUES(?,?,?)";
        self.cursor.execute(query,(sid,score,comment));
        self.con.commit()
    def removeItem(self,tableName,sid):
        query = f"DELETE FROM '{tableName}' WHERE Sid = {sid}";
        self.cursor.execute(query);
        self.con.commit();
    def updateItem(self,courseName,tableName,sid,newScore,newComment):
        table = courseName+tableName;
        query = f"UPDATE '{table}' SET Score = ? , Comment = ? WHERE Sid = ?";
        self.cursor.execute(query,(newScore,newComment,sid));
        self.con.commit();
    def fetch(self,tableName):
        query = f"SELECT * FROM '{tableName}'"
        self.cursor.execute(query);
        rows = self.cursor.fetchall()
        return rows;
    def getTableColumns(self,tableName):
        self.cursor.execute(f"PRAGMA table_info({tableName})");
        return [row[1] for row in self.cursor.fetchall()];
    def getTableRows(self,tableName):
        self.cursor.execute(f"SELECT DISTINCT * FROM '{tableName}'");
        return self.cursor.fetchall();
    def getName(self,sid,courseName):
        table = courseName+"Students";
        query = f"SELECT SName FROM '{table}' WHERE Sid = ?";
        name = self.cursor.execute(query,(sid,)).fetchone();
        return name[0] if name else None;
    def finalize(self, courseName):
        infoTable = f"{courseName}AssessmentInfo"
        try:
            self.cursor.execute(f"SELECT tableName FROM '{infoTable}'")
            tables = [row[0] for row in self.cursor.fetchall()]
        except sqlite3.OperationalError:
            tables = []
        baseQuery = f"SELECT '{courseName}Students'.Sid,'{courseName}Students'.SName"
        joinClauses = ""
        for table in tables:
            baseQuery += f", '{table}'.Score AS '{table}_Score'"
            joinClauses += f" LEFT JOIN '{table}' ON '{courseName}Students'.Sid = '{table}'.Sid"
        finalQuery = baseQuery + f" FROM '{courseName}Students' " + joinClauses + ";"
        print("Executing:\n", finalQuery)
        self.cursor.execute(finalQuery)
        rows = self.cursor.fetchall()
        return rows
    def finalizeTable(self,courseName):
        finalizedTable = f"{courseName}Finalized";
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",(courseName+"%",));
        tables = [row[0] for row in self.cursor.fetchall()];
        columns = ["Sid INTEGER PRIMARY KEY","SName TEXT"];
        for table in tables:
            if table.endswith("Students") or table.endswith("Finalized"):
                continue;
            scoreCol = f"{table}_Score INTEGER";
            columns.append(scoreCol);
            columnDefinitions = ', '.join(columns);
            createQuery = f"CREATE TABLE IF NOT EXISTS '{finalizedTable}'({columnDefinitions})";
            self.cursor.execute(createQuery);
            self.con.commit();
            self.cursor.execute(f"DELETE FROM '{finalizedTable}'");
            rows = self.finalize(courseName);
            placeHolders = ', '.join(["?"]*len(rows[0])) if rows else "?,?";
            insertQuery = f"INSERT INTO '{finalizedTable}' VALUSE({placeHolders})";
            self.cursor.execute(insertQuery,rows);
            self.con.commit();
    def createAssessmentInfoTable(self,courseName):
        query = f"CREATE TABLE IF NOT EXISTS '{courseName}AssessmentInfo'(tableName TEXT PRIMARY KEY , baseGrade INTEGER)"
        self.cursor.execute(query)
        self.con.commit()
    def getBaseGrade(self,courseName,tableName):
        self.cursor.execute(f"SELECT baseGrade FROM '{courseName}AssessmentInfo' WHERE tableName=?",(courseName+tableName,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    def getColumnValues(self,tableName,columnValue):
        self.cursor.execute(f"SELECT {columnValue} FROM '{tableName}'")
        rows = self.cursor.fetchall()
        return [r[0] for r in rows]
    def getRows(self,tableName):
        query = f"SELECT * FROM '{tableName}'" 
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return rows
    def __del__(self):
        self.cursor.close();
        self.con.close();