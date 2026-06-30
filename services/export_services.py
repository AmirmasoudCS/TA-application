import csv
import os
from datetime import datetime
import pandas as pd
class ExportServices:
    def __init__(self,export_directory="exports"):
        self.export_directory = export_directory;
        os.makedirs(self.export_directory,exist_ok=True);
    def _generate_filename(self,base_name,extension):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S");
        clean_name = base_name.replace(" ","_");
        return f"{self.export_directory}/{clean_name}_{timestamp}.{extension}";
    def exportToCSV(self,rows,columns,filename="students"):
        filepath = self._generate_filename(filename, "csv")
        with open(filepath,mode='w',newline="",encoding="utf-8") as file:
            writer = csv.writer(file);
            writer.writerow(columns);
            writer.writerows(rows);
        return filepath;
    def exportToExcel(self,rows,columns,filename="students"):
        filepath=self._generate_filename(filename, "xlsx");
        df = pd.DataFrame(rows,columns=columns);
        df.to_excel(filepath,index=False);
        return filepath;