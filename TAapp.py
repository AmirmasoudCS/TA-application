from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import font
import sys
import os
from tkinter import filedialog
import csv
from openpyxl import Workbook
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
from config import DB_PATH, EXPORT_DIRECTORY
from tkinter import colorchooser
from configure_styles import MyStyle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from reportlab.lib import colors
#from reportlab.lib.pagesizes import letter, landscape
#from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
################# Global Variables #################### 
main_window = Tk()
main_window.option_add("*TEntry*Font", ("Inter", 12, "bold"));
main_window.option_add("*TEntry*justify", "center")
main_window.title("Teacher Assistant Application");
main_window.geometry("1400x800");
main_window.attributes('-fullscreen', True);
for r in range(5):      
    main_window.rowconfigure(r, weight=0)
main_window.rowconfigure(2, weight=1)   
for c in range(11):     
    main_window.columnconfigure(c, weight=1)
main_window.resizable(0,0);
#main_window.withdraw();
#main_window.after(0,main_window.withdraw)
from teacherAssistantAppDB import Database
db = Database(DB_PATH);
course_window = None;
filename_window = None;
escape_menu = None;
escMenuIsOpen = False; 
headFont = font.Font(family="Inter",size=16,weight="bold");
bodyFont= font.Font(family="Inter",size=12,weight="bold");
titleFont = font.Font(family="Inter",size=20,weight='bold');
sortStates={};
############### Styles ###############
theme = MyStyle()
theme.loadTheme()
theme.apply(main_window)
#################### Entry Variables ################## 
courseText = StringVar(main_window)
filenameText = StringVar(main_window)
nameText = StringVar(main_window)
idText = IntVar(main_window)
scoreText = IntVar(main_window)
tableText = StringVar(main_window)
removeIdText = IntVar(main_window)
commentText = StringVar(main_window);
searchVar = StringVar(main_window);
baseGradeVar = IntVar(main_window)
################# Functions ##################### 
def showHistogram(tableName):
    fullTableName = courseText.get().upper()+tableName
    rows = db.getTableRows(fullTableName)
    columns = db.getTableColumns(fullTableName)
    scoreIndex = columns.index("Score")
    scores =[]
    for row in rows :
        scores.append(row[scoreIndex])
    popup = Toplevel(main_window)
    popup.overrideredirect(True)
    popup.configure(bg=theme.BG)
    popup.grid_rowconfigure(1, weight=1)
    popup.grid_columnconfigure(0, weight=1)
#   popup.title("Score Histogram")
    titleBar = ttk.Frame(popup,height=30)
    titleBar.grid(row=0,column=0,sticky='ew')
    titleBar.grid_columnconfigure(0, weight=1)
    titleLabel=ttk.Label(titleBar,text = "Score Histogram")
    titleLabel.grid(row=0,column=0,sticky='w',padx=10,pady=5)
    closeBTN=ttk.Button(titleBar,text="✕",command=popup.destroy)
    closeBTN.grid(row=0,column=1,sticky='e',padx=8)
    content=ttk.Frame(popup)
    content.grid(row=1,column=0,sticky='nsew')    
    popup.geometry("800x550")
    fig,ax=plt.subplots()
    fig.patch.set_facecolor(theme.BG)
    #fig.tight_layout()
    ax.set_facecolor(theme.CARD)
    ax.hist(scores,bins=10,edgecolor=theme.BORDER,color=theme.PURPLE)
    ax.set_title("Score Distribution",color=theme.FG)
    ax.set_xlabel("Scores",color=theme.FG)
    ax.set_ylabel("Number of Students",color=theme.FG)
    ax.grid(color=theme.BORDER, linestyle="--", alpha=0.3)
    ax.tick_params(colors=theme.FG)
    for spine in ax.spines.values():
        spine.set_color(theme.BORDER)
    canvas = FigureCanvasTkAgg(fig,master = content)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0,column=0,sticky='nsew')
    content.grid_rowconfigure(0, weight=1)
    content.grid_columnconfigure(0, weight=1)
    centerWindow(popup, main_window)
    def startMove(event):
        popup.x = event.x
        popup.y = event.y
    def moveWindow(event):
        popup.geometry(f"+{event.x_root - popup.x}+{event.y_root - popup.y}")
    titleBar.bind("<Button-1>",startMove)
    titleBar.bind("<B1-Motion>",moveWindow)
def change_theme(theme_name,window_name):
    theme.loadTheme()
    theme.apply(main_window)
    if window_name is not None and window_name.winfo_exists():
        theme.apply(window_name)
def lookupStudentName(event=None):
    try:
        sid = str(idText.get()).strip()
    except Exception:
        nameLookupLabel.config(text="Name: ---")
        return
    if not sid:
        nameLookupLabel.config(text="Name: ---")
        return
    try:
        name = db.getName(int(sid),courseText.get().upper())
    except:
        name = None;
    if name is not None :
        if name != "":
            nameLookupLabel.config(text=f"Name: {name}")
        else:
            nameLookupLabel.config(text=f"Name: ---")
    else:
        nameLookupLabel.config(text=f"Name: Not found")
def createTitleBar(window,title):
    def startMove(event):
        window._x = event.x
        window._y = event.y
    def doMove(event):
        x = event.x_root - window._x
        y = event.y_root - window._y
        window.geometry(f"+{x}+{y}")
    def closeWindow():
        try:
            window.master.attributes("-disabled",False)
        except Exception as e:
            print(f"Error re-enabling main window {e}")
        window.destroy()
        try:
            window.master.focus_force()
        except:
            pass
    window.overrideredirect(True)
    titleBar = ttk.Frame(window)
    titleBar.grid(row=0, column=0, sticky="ew")
    window.grid_columnconfigure(0, weight=1)
    titleLabel = ttk.Label(titleBar, text=title)
    titleLabel.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    closeBtn = ttk.Button(titleBar,text="✕",command=closeWindow,width=3)
    closeBtn.grid(row=0,column=1,padx=5,pady=5,sticky="e")
    titleBar.grid_columnconfigure(0, weight=1)
    titleBar.bind("<Button-1>", startMove)
    titleBar.bind("<B1-Motion>", doMove)
    titleLabel.bind("<Button-1>", startMove)
    titleLabel.bind("<B1-Motion>", doMove)
    return titleBar
def openSettingsMenu():
    global currentThemeColor;
    toggleEscMenu();
    settings_window = Toplevel(main_window);
    createTitleBar(settings_window,"Settings")
    settings_window.focus_force()
    content = ttk.Frame(settings_window)
    content.grid(row=1,column=0,sticky='nsew',padx=10,pady=10)
    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=1)
    settings_window.grid_rowconfigure(1, weight=1)
    settings_window.resizable(False,False);
    settings_window.configure(bg=theme.BG);
    settings_window.attributes("-topmost",True);
    settings_window.after(100, lambda: settings_window.attributes("-topmost",False));
    #ttk.Label(content,text="Settings").grid(row=1,column=0,columnspan=2,pady=(10,15));
    themeFrame = ttk.LabelFrame(content,text="Theme Color",padding=5,style="Settings.TLabelframe");
    themeFrame.grid(padx=10,pady=10,row=2,column=0,columnspan=2);
    themeFrame.columnconfigure(0, weight=1)
    themeFrame.columnconfigure(1, weight=1)
    ### Themese ###
    defaultColorBTN=ttk.Button(themeFrame,text="Default (Purple)",command=lambda :(theme.theme_default(),theme.apply(main_window),theme.saveTheme("default"),change_theme('default',settings_window)))
    darkThemeBTN=ttk.Button(themeFrame,text="Dark",command=lambda :(theme.theme_dark(),theme.apply(main_window),theme.saveTheme("dark"),change_theme('dark',settings_window)))
    blueThemeBTN=ttk.Button(themeFrame,text="Blue",command=lambda :(theme.theme_blue(),theme.apply(main_window),theme.saveTheme("blue"),change_theme('blue',settings_window)))
    greenThemeBTN=ttk.Button(themeFrame,text="Green",command=lambda:(theme.theme_green(),theme.apply(main_window),theme.saveTheme("green"),change_theme('green',settings_window)))
    redThemeBTN=ttk.Button(themeFrame,text="Red",command=lambda :(theme.theme_red(),theme.apply(main_window),theme.saveTheme("red"),change_theme('red',settings_window)))
    yellowThemeBTN=ttk.Button(themeFrame,text="Yellow",command=lambda:(theme.theme_yellow(),theme.apply(main_window),theme.saveTheme("yellow"),change_theme('yellow',settings_window)))
    pinkThemeBTN=ttk.Button(themeFrame,text="Pink",command=lambda :(theme.theme_pink(),theme.apply(main_window),theme.saveTheme("pink"),change_theme('pink',settings_window)))
    jigariThemeBTN = ttk.Button(themeFrame,text="Jigari",command=lambda:(theme.theme_jigari(),theme.apply(main_window),theme.saveTheme("jigari"),change_theme('jigari',settings_window)))
    defaultColorBTN.grid(row=0,column=0,padx=5,pady=5,sticky='ew')
    darkThemeBTN.grid(row=0,column=1,padx=5,pady=5,sticky='ew')
    blueThemeBTN.grid(row=1,column=0,padx=5,pady=5,sticky='ew')
    greenThemeBTN.grid(row=1,column=1,padx=5,pady=5,sticky='ew')
    redThemeBTN.grid(row=2,column=0,padx=5,pady=5,sticky='ew')
    yellowThemeBTN.grid(row=2,column=1,padx=5,pady=5,sticky='ew')
    pinkThemeBTN.grid(row=3,column=0,padx=5,pady=5,sticky='ew')
    jigariThemeBTN.grid(row=3,column=1,padx=5,pady=5,sticky='ew')
    
    ### Course ###
    courseFrame = ttk.LabelFrame(content,text="Change Course",padding=10,style="Settings.TLabelframe");
    courseFrame.grid(row=3,column=0,columnspan=2,padx=10,pady=10,sticky='ew');
    ttk.Label(courseFrame,text="Enter new course name: ").grid(row=0,column=0,sticky='w',pady=3);
    newCourseVar = StringVar();
    newCourseEntry= ttk.Entry(courseFrame,textvariable=newCourseVar,width=30);
    newCourseEntry.grid(row=1,column=0,pady=3);
    newCourseEntry.bind("<Return>",lambda e=None :newFilenameEntry.focus_set());
    ttk.Label(courseFrame,text="Enter filename: ",).grid(row=2,column=0,sticky='w',pady=3);
    newFilenameVar = StringVar();
    newFilenameEntry = ttk.Entry(courseFrame,textvariable=newFilenameVar,width=30);
    newFilenameEntry.grid(row=3,column=0,pady=3);
    newFilenameEntry.bind("<Return>",lambda e : applyCourseBtn.invoke());
    def applyNewCourse():
        name = newCourseVar.get().upper();
        file = newFilenameVar.get().upper();
        if name == "" or file == "":
            messagebox.showwarning("Missing Input","Please fill both course name and filename.");
            return;
        courseText.set(name);
        filenameText.set(file);
        messagebox.showinfo("Course Updated",f"Course set to : {name}\nFile : {file}");
        settings_window.destroy();
        main_window.withdraw();
        openFilenameWindow();
        global submitFilenameBtn;
        submitFilenameBtn.invoke();
    applyCourseBtn = ttk.Button(courseFrame,text="Apply New Course", command=applyNewCourse);
    applyCourseBtn.grid(row=4,column=0,columnspan=2,pady=10);
    ttk.Button(content,text="Close Settings",command=lambda: (main_window.attributes("-disabled", False), settings_window.destroy())).grid(row=5,column=0,columnspan=2,padx=5,pady=5)
    settings_window.transient(main_window);
    settings_window.update_idletasks();
    centerWindow(settings_window,main_window);
    main_window.attributes("-disabled", True)
def onClickOutside(event):
    global escape_menu,escMenuIsOpen;
    if not escMenuIsOpen or not escape_menu :
        return;
    x = event.x_root;
    y= event.y_root;
    menu_x = escape_menu.winfo_rootx();
    menu_y= escape_menu.winfo_rooty();
    menu_w=escape_menu.winfo_width();
    menu_h=escape_menu.winfo_height();
    inside = (menu_x <= x <= menu_x + menu_w) and (menu_y <= y <= menu_y + menu_h);
    if not inside:
        toggleEscMenu();
def closeApplication(event=None):
    global main_window,escape_menu;
    escape_menu.lower(); # type: ignore 
    confirmation = messagebox.askyesno("Confirm Exit","Are you sure you want to close the application?");
    if confirmation:
        main_window.destroy();
    else:
        escape_menu.lift(); # type: ignore
def toggleEscMenu(event=None):
    global escape_menu,escMenuIsOpen;
    if escMenuIsOpen:
        if escape_menu:
            escape_menu.destroy();
        escape_menu = None;
        escMenuIsOpen = False;
        return;
    escape_menu = Toplevel(main_window);
    escape_menu.columnconfigure(0, weight=1)
    escape_menu.columnconfigure(1, weight=1)
    escape_menu.columnconfigure(2, weight=1)
    escape_menu.overrideredirect(True);
    escape_menu.configure(bg=theme.PURPLE,highlightthickness=3,highlightbackground="black",highlightcolor="black"); # type: ignore
    escape_menu.attributes("-topmost",True);
    width = 260;
    height=340;
    escape_menu.geometry(f"{width}x{height}+0+0");
    centerWindow(escape_menu,main_window);
    menuLabel=ttk.Label(escape_menu,text="Menu",style="MenuLabel.TLabel");
    menuLabel.grid(row=0,column=1,pady=5,padx=5,sticky='n');
    closeBorder=Frame(escape_menu,bg='black',bd=0);
    closeBorder.grid(row=1,column=1,pady=5,padx=5,sticky='n');
    closeBTN = ttk.Button(closeBorder,text="Close Application",command=closeApplication,style="MenuButtons.TButton");
    closeBTN.grid(row=0,column=0,pady=2,padx=2,sticky='n');
    settingsBorder=Frame(escape_menu,bg='black',bd=0);
    settingsBorder.grid(row=2,column=1,pady=5,padx=5,sticky='n');
    settingBTN = ttk.Button(settingsBorder,text='Settings',command=openSettingsMenu,style="MenuButtons.TButton");
    settingBTN.grid(row=0,column=0,pady=2,padx=2,sticky='n');
    main_window.bind("<Button-1>",onClickOutside);
    escMenuIsOpen =True;
def getCurrentTableView():
    global tableView;
    return tableView;
def toCSV(tree):
    filePath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files","*.csv","*.txt")], # type: ignore
        title="Save as CSV",
        initialdir=EXPORT_DIRECTORY
    )
    if not filePath:
        return;
    columns = tree["columns"];
    rows = [];
    for iid in tree.get_children(""):
        row = [tree.set(iid,col) for col in columns];
        rows.append(row);
    try:
        with open(filePath,mode='w',newline="",encoding='utf-8') as f:
            writer = csv.writer(f,quoting=csv.QUOTE_MINIMAL,delimiter=";");
            writer.writerow(columns);
            writer.writerows(rows);
        messagebox.showinfo("Success!","CSV exported successfully!");
    except Exception as e:
        messagebox.showerror("Erorr",str(e));
def toExcel(tree):
    filePath= filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Workbook","*.xlsx")],
        title="Save as Excel",
        initialdir=EXPORT_DIRECTORY
        )
    if not filePath:
        return;
    wb = Workbook();
    ws = wb.active;
    ws.append(tree["columns"]); # type: ignore
    for iid in tree.get_children(""):
        ws.append([tree.set(iid,col) for col in tree["columns"]]); # type: ignore
    try:
        wb.save(filePath);
        messagebox.showinfo("Success!","Excel file exported successfully!");
    except Exception as e:
        messagebox.showerror("Erorr",str(e));
def updateHeaders(tree,sortedCol,reverse):
    for col in tree["columns"]:
        base = col;
        if col == sortedCol:
            arrow = "▼" if reverse else "▲";
            base = f"{col} {arrow}";
        tree.heading(col,text=base);
def sortColumns(tree,col,reverse):
    data =[];
    for iid in tree.get_children(""):
        raw = tree.set(iid,col);
        if not isinstance(raw,str):
            try:
                raw = str(raw);
            except:
                raw ="";
        data.append((raw,iid));    
    def tryNumeric(v):
        try:
            return float(v);
        except:
            return v.lower() if isinstance(v,str) else v;
    data.sort(key=lambda item: tryNumeric(item[0]),reverse=reverse);
    for index,(val,iid) in enumerate(data):
        tree.move(iid,"",index);
    sortStates[col] = not reverse;
    updateHeaders(tree,col,reverse);
    tree.heading(col,command=lambda: sortColumns(tree,col,not reverse));
def filterTreeView():
    tableName = tableText.get()
    if not tableName:
        return
    query = searchVar.get().strip();
    for row in tableView.get_children():
        tableView.delete(row);
    tableName = courseText.get().upper()+tableText.get()
    cursor = db.cursor;
    if query == "":
        cursor.execute(f"SELECT * FROM '{tableName}'");
    else:
        cursor.execute(f"SELECT * FROM '{tableName}' WHERE Sid LIKE ?",(query +"%",));
    rows = cursor.fetchall()
    columns = list(tableView["columns"])
    baseGrade = db.getBaseGrade(courseText.get().upper(), tableText.get())
    calculatedIndex = columns.index("Calculated") if "Calculated" in columns else None
    scoreIndex = columns.index("Score") if "Score" in columns else None
    for row in rows:
        rowlist = list(row)
        if calculatedIndex is not None and scoreIndex is not None and baseGrade:
            score = row[scoreIndex]
            if isinstance(score, (int,float)):
                calculated = round((score/100)*baseGrade,2)
            else:
                calculated =""
            rowlist.insert(calculatedIndex,calculated)
        tableView.insert("","end",values=rowlist);
def selectTable():
    main_window.rowconfigure(2, weight=1)
    tableName = tableText.get();
    if tableName =="":
        messagebox.showwarning("Input Error","Please fill the Table to present field.");
        return;
    fullTableName = courseText.get().upper()+tableName
    if tableName.endswith("Students"):
        db.createTable(tableName,filenameText.get().upper(),courseText.get().upper())
    elif not db.tableExists(tableName,courseText.get().upper()):
        askBaseGrade()
        return
    columns = db.getTableColumns(courseText.get().upper()+tableName);
    if not tableName.endswith("Students"):
        columns = list(columns)
        lowerCols = [c.lower() for c in columns]
        if "comment" in lowerCols:
            comment_index = lowerCols.index("comment")
            columns.insert(comment_index, "Calculated")
        else:
            columns.append("Calculated")
    rows=db.getTableRows(courseText.get().upper()+tableName);
    baseGrade = db.getBaseGrade(courseText.get().upper(),tableName)
    if not columns:
        messagebox.showinfo("No Columns",f"table '{tableName}' has no columns.");
        return;
    for widget in tableFrame.winfo_children():
        widget.destroy();
    y_scrollbar = ttk.Scrollbar(tableFrame,orient="vertical");
    y_scrollbar.pack(side='right',fill='y');
    x_scrollbar = ttk.Scrollbar(tableFrame,orient="horizontal");
    x_scrollbar.pack(side="bottom",fill='x');
    global tableView;
    tableView = ttk.Treeview(tableFrame,columns=columns,show="headings",height = 10,yscrollcommand=y_scrollbar.set,xscrollcommand=x_scrollbar.set);
    for col in columns:
        if col.lower() in ("score","sid"):
            tableView.column(col,width = 80,stretch=False,anchor = 'center');
        elif col.lower() == "calculated":
            tableView.column(col,width=80,stretch=False,anchor='center')
        elif col.lower() == "comment":
            tableView.column(col,width = 400,stretch=True,anchor = 'w');
        else:
            tableView.column(col,width = 150,stretch = True,anchor = 'center');
        tableView.heading(col,text=col,command=lambda c=col: sortColumns(tableView,c,False));
    tableView.pack(fill='both',expand=True);
    y_scrollbar.config(command=tableView.yview);
    x_scrollbar.config(command=tableView.xview);
    calculatedIndex=columns.index("Calculated") if "Calculated" in columns else None
    for row in rows:
        if not tableName.endswith("Students") and baseGrade:
            lowerCols = [c.lower() for c in columns]
            scoreIndex = lowerCols.index("score") if "score" in lowerCols else None
            score = row[scoreIndex] if scoreIndex is not None else None
            if isinstance(score,(int,float)):
                calculated = round((score/100)*baseGrade,2)
            else:
                calculated=""
            rowList = list(row)
            rowList.insert(calculatedIndex,calculated) # type: ignore
            tableView.insert("","end",values=rowList)
        else:
            tableView.insert("","end",values=row);              
    showGradeStats(rows, tableName)
    tableView.bind("<Return>",lambda e : selectTable())
def centerWindow(window, parent):
    parent.update_idletasks()
    window.update_idletasks()
    parent_x =parent.winfo_x()
    parent_y =parent.winfo_y()
    parent_width =parent.winfo_width()
    parent_height =parent.winfo_height()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    center_x = parent_x + (parent_width // 2) - (window_width // 2)
    center_y = parent_y + (parent_height // 2) - (window_height // 2)
    window.geometry(f"+{center_x}+{center_y}")
def on_window_close(event=None):
    print("Closing window, exiting application.") 
    if course_window:
        course_window.destroy()
    if filename_window:
        filename_window.destroy()
    main_window.destroy()
    sys.exit()
def addItem():
    studentId = idText.get();
    studentScore = scoreText.get();
    if not studentScore or not studentId :
        messagebox.showwarning("Input Error","Please fill both id and score fields.");
        return;
    openCommentWindow(studentId,studentScore);
    idText.set(""); # type: ignore
    scoreText.set(""); # type: ignore
    commentText.set(""); # type: ignore
    global nameLookupLabel
    nameLookupLabel.config(text="Name: ---")
def removeItem():
    studentId = removeIdText.get();
    if not studentId:
        messagebox.showwarning("Input Error","Please fill id field.");
        return;
    db.removeItem(courseText.get().upper()+tableText.get(),studentId);
    selectTable();
    removeIdText.set(""); # type: ignore
def finalizeCourse():
    courseName = courseText.get().upper();
    if courseName == "":
        messagebox.showwarning("Input Error","Please enter a course name.");
        return;
    rows = db.finalize(courseName);
    if not rows:
        pass;
    columnNames = [desc[0] for desc in db.cursor.description];
    for widget in tableFrame.winfo_children():
        widget.destroy();
    y_scrollbar = ttk.Scrollbar(tableFrame, orient="vertical")
    y_scrollbar.pack(side='right', fill='y')
    x_scrollbar = ttk.Scrollbar(tableFrame, orient="horizontal")
    x_scrollbar.pack(side="bottom", fill='x')
    global tableView;
    tableView = ttk.Treeview(tableFrame,show="headings",height=10,yscrollcommand=y_scrollbar.set,xscrollcommand=x_scrollbar.set);
    prefix = courseText.get().upper()
    cleanedColumns = [];
    columnMap ={};
    for c in columnNames:
        newName = c.removeprefix(prefix) if c.startswith(prefix) else c ;
        cleanedColumns.append(newName);
        columnMap[newName] = c;
    tableView["columns"]=cleanedColumns;
    for col in cleanedColumns:
        if col.lower() in ("sid","sname"):
            if col.lower() == "sname":
                tableView.column(col,width=185,anchor='center',stretch=False);
            else:
                tableView.column(col,width=80,anchor='center',stretch=False);
        else :
            tableView.column(col, width=90 ,stretch=True, anchor = 'center');
        tableView.heading(col,text=col);
    tableView.pack(fill='both',expand=True);
    y_scrollbar.config(command=tableView.yview);
    x_scrollbar.config(command=tableView.xview);
    for row in rows:
        values = [];
        for cleanCol in cleanedColumns:
            originalColumn = columnMap[cleanCol];
            idx = columnNames.index(originalColumn);
            values.append(row[idx]);
        tableView.insert("","end",values=values);
    global tabelText;
    #tableText.set("Finalized");
    messagebox.showinfo("Success!","Course has been finalized!");
def showGradeStats(rows,tableName):
    if not("Problem" in tableName or "Quiz" in tableName):
        return
    fullTableName = courseText.get().upper()+tableName
    columns=db.getTableColumns(fullTableName)
    if "Score" not in columns:
        return
    scores = db.getColumnValues(courseText.get().upper()+tableName,"Score")
    scores = [s for s in scores if isinstance(s,(int,float))]
    if not scores:
        return
    baseGrade=db.getBaseGrade(courseText.get().upper(),tableName)
    avgScore=sum(scores)/len(scores)
    highest=max(scores)
    lowest=min(scores)
    if baseGrade:
        percentAvg=avgScore
        percentHigh=highest
        percentLow=lowest
        stat_text=(
            f"Base Grade: {baseGrade} | "
            f"Average: {avgScore:.2f} ({percentAvg:.2f}%) | "
            f"Highest: {highest:.2f} ({percentHigh:.2f}%) | "
            f"Lowest: {lowest:.2f} ({percentLow:.2f}%)"
            )
    else:
        stat_text=(f"Average {avgScore:.2f} | Highest: {highest:.2f} | Lowest: {lowest:.2f}")
    global statsLabel
    statsLabel.config(text=stat_text)
############## Windows ############## 
def askBaseGrade():
    popup = Toplevel(main_window)
    #createTitleBar(popup,"Base Grade")
    popup.title("Base Grade")
    popup.geometry("250x150")
    popup.resizable(0,0) # type: ignore
    popup.configure(bg=theme.BG) # type: ignore
    popup.grid_columnconfigure(0,weight=1)
    popup.grid_columnconfigure(1,weight=1)
    popup.grid_columnconfigure(2,weight=1)
    ttk.Label(popup,text="Base grade for "+tableText.get()).grid(row=0,column=1)
    entry = ttk.Entry(popup,textvariable=baseGradeVar,width=10)
    entry.grid(row=1,column=1)
    entry.focus_set()
    def submit(event=None):
        base = baseGradeVar.get()
        db.createTable(tableText.get(),filenameText.get().upper(),courseText.get().upper(),base)
        popup.destroy()
        selectTable()
    cBTN = ttk.Button(popup,text="Create Table",command=submit)
    cBTN.grid(row=2,column=1)
    entry.bind("<Return>",lambda e :cBTN.invoke())
    popup.transient(main_window)
    popup.grab_set()
    centerWindow(popup,main_window)
def openUpdateWindow():
    selected = tableView.selection();
    if not selected :
        messagebox.showwarning("Selection Required","Please select a row to update.");
        return;
    values = tableView.item(selected[0],'values');
    sid = values[0];
    score = values[1];
    calculated= values[2]
    comment = values[3] if len(values) > 3  else "";
    updatePopup = Toplevel(main_window);
    #createTitleBar(updatePopup,"Update Record")
    updatePopup.title("Update Record");
    updatePopup.resizable(0,0);# type: ignore
    updatePopup.configure(bg=theme.BG); # type: ignore
    updatePopup.grid_columnconfigure(0,weight=1);
    updatePopup.grid_columnconfigure(2, weight=1);
    # SID (read-only)
    ttk.Label(updatePopup,text="ID",).pack(pady=(10,2));
    sidLabel = ttk.Label(updatePopup,text=sid,anchor='center',width=30,style="sidStyle.TLabel");
    sidLabel.pack(pady=5);
    # Score
    ttk.Label(updatePopup,text="Score").pack(pady=(10,2));
    scoreVar = StringVar(value=score);
    scoreEntry = ttk.Entry(updatePopup,textvariable=scoreVar,width=40);
    scoreEntry.pack(pady=10,ipady=4);
    scoreEntry.focus_set();
    scoreEntry.icursor(END);
    scoreEntry.select_range(END,END);
    # Comment
    ttk.Label(updatePopup,text = "Comment").pack(pady=(10,2));
    commentVar = StringVar(value = comment);
    commentEntry = ttk.Entry(updatePopup,textvariable=commentVar,width=30);
    commentEntry.pack(pady=5);
    # Submit Update
    def submitUpdate():
        newScore = scoreVar.get();
        newComment = commentVar.get();
        db.updateItem(courseText.get().upper(),tableText.get(),sid,newScore,newComment);
        updatePopup.destroy();
        selectTable();
        for item in tableView.get_children():
            row = tableView.item(item,"values");
            if row and row[0] == sid:
                tableView.selection_set(item);
                tableView.see(item);
                break;
    saveUpdateBTN = ttk.Button(updatePopup,text="Save Update",command = submitUpdate);
    saveUpdateBTN.pack(pady=15);
    updatePopup.bind("<Return>", lambda e=None:saveUpdateBTN.invoke());
    updatePopup.transient(main_window);
    updatePopup.grab_set();
    centerWindow(updatePopup,main_window);    
def openCourseWindow():
    global course_window;
    global main_window;
    main_window.withdraw()
    course_window = Toplevel(main_window);
    course_window.lift()
    course_window.focus_force()
    #createTitleBar(course_window, "Enter Course Name")
    course_window.title("Enter Course Name");
    course_window.geometry("300x200");
    course_window.resizable(0,0); # type: ignore
    course_window.configure(bg=theme.BG); # type: ignore
    course_window.grid_columnconfigure(0, weight=1);
    course_window.grid_columnconfigure(2, weight=1);
    ttk.Label(course_window,text="Enter Course: ",).grid(row=1,column=1,pady=10);
    courseEntry = ttk.Entry(course_window,textvariable=courseText,width=30);
    courseEntry.grid(row=2,column=1,pady=5,padx=10);
    courseEntry.focus_set();
    submitCourseBtn = ttk.Button(course_window,text="Submit",command=openFilenameWindow,width=10);
    submitCourseBtn.grid(row=3,column=1,pady=10);
    centerWindow(course_window, main_window);
    course_window.bind('<Return>', lambda event=None : submitCourseBtn.invoke());
    course_window.update_idletasks();
    course_window.lift();
    course_window.focus_force();
    courseEntry.focus_set();
    course_window.protocol("WM_DELETE_WINDOW",on_window_close);
def openFilenameWindow():
    global filename_window;
    global course_window;
    if courseText.get().upper() == "":
        messagebox.showwarning("Input Error","Please enter a course name.");
        return;
    if course_window : 
        course_window.destroy()
    messagebox.showinfo("Confirmation",f"Course : {courseText.get().upper()}");
    filename_window= Toplevel(main_window);
    filename_window.title("Enter Filename");
    filename_window.geometry("300x200");
    filename_window.resizable(0,0); # type: ignore
    filename_window.configure(bg=theme.BG); # type: ignore
    filename_window.grid_columnconfigure(0, weight=1);
    filename_window.grid_columnconfigure(2, weight=1);
    ttk.Label(filename_window,text="Enter Filename: " ).grid(row=0,column=1,pady=10);
    filenameEntry = ttk.Entry(filename_window,textvariable=filenameText,width=30);
    filenameEntry.grid(row=2,column=1,pady=5,padx=10);
    filename_window.update_idletasks();
    filename_window.lift();
    filename_window.focus_force();
    filenameEntry.focus_set();
    global submitFilenameBtn;
    submitFilenameBtn = ttk.Button(filename_window,text="Submit",command = openMainWindow,width=10);
    submitFilenameBtn.grid(row=3,column=1,pady=10);
    centerWindow(filename_window, main_window);
    filename_window.bind('<Return>',lambda event = None : submitFilenameBtn.invoke());
    filename_window.protocol("WM_DELETE_WINDOW",on_window_close);
def openCommentWindow(sid,score):
    popup = Toplevel(main_window);
    popup.title("Add Comment");
    popup.geometry("350x200");
    popup.resizable(0,0); # type: ignore
    popup.configure(bg=theme.BG); # type: ignore
    popup.grid_columnconfigure(0, weight=1);
    popup.grid_columnconfigure(2, weight=1);
    name = db.getName(sid,courseText.get().upper());
    ttk.Label(popup,text=f"Any comment for '{name}' score?").pack(pady=10);
    commentEntry = ttk.Entry(popup,textvariable=commentText,width=40);
    commentEntry.pack(pady=10);
    commentEntry.focus_set();
    def submitComment():
        comment_text = commentText.get();
        db.addItem(courseText.get().upper()+tableText.get(), sid, score,comment_text);
        popup.destroy();
        selectTable();
        global idEntry;
        idEntry.focus_set();
    submitBTN = ttk.Button(popup,text="Submit",command=submitComment);
    submitBTN.pack(pady=10);
    popup.bind("<Return>",lambda event=None: submitBTN.invoke());
    popup.transient(main_window);
    popup.grab_set();
    centerWindow(popup,main_window);
def openMainWindow():
    global filename_window;
    filename = filenameText.get().upper();
    if filename == "":
        messagebox.showwarning("Input Error","Please enter a file name.");
        return;
    if filename_window:
        filename_window.destroy()
    if not filename.endswith(".txt"):
        filename+=".txt";
    fullPath = os.path.join(EXPORT_DIRECTORY, filename.upper());
    messagebox.showinfo("Confirmation",f"Course : {courseText.get().upper()}\nFilename : {filename}");
    db.createStudentsTable(courseText.get().upper()+"Students");
    db.populateStudents(fullPath, courseText.get().upper()+"Students");
    db.createAssessmentInfoTable(courseText.get().upper())
#######
    main_window.deiconify()
    
######################################
    main_window.rowconfigure(2, weight=0)
#######################################################
############# Frames ##################################
    informationFrame = ttk.LabelFrame(main_window,padding=(5,2),text="Information");
    addFrame = ttk.LabelFrame(main_window,text='Add Students',padding=(5,2));
    removeFrame = ttk.LabelFrame(main_window,text='Remove Students',padding=(5,2));
    selectTableFrame = ttk.LabelFrame(main_window,text="Select Table",padding=(5,2));
    
    informationFrame.grid(row=0,column=0,columnspan=10,sticky='ew',padx=20,pady=5);
    selectTableFrame.grid(row=1 , column=0,columnspan=10,sticky='ew',padx=20,pady=5);
    addFrame.grid(row = 3 , column=0,columnspan=10,sticky='ew',padx=20,pady=5);
    removeFrame.grid(row=4,column=0,columnspan=10,sticky='ew',padx=20,pady=5);
    global tableFrame;
    tableOuter = ttk.Frame(main_window,borderwidth=1,relief='solid');
    tableOuter.grid(row=2,column=0,columnspan=10,sticky='nsew',padx=10,pady=5);
    tableOuter.grid_rowconfigure(0, weight=1)
    tableOuter.grid_columnconfigure(0, weight=1)
    tableFrame = ttk.Frame(tableOuter);
    tableFrame.grid(row=2,column=0,columnspan=10,padx=10,pady=5,sticky="nsew");
    tableFrame.grid_rowconfigure(0, weight=1);
    tableFrame.grid_columnconfigure(0, weight=1);
    tableFrame.grid_propagate(True);
    
    for c in range(10):
        addFrame.grid_columnconfigure(c, weight=1)
    for c in range(10):
        removeFrame.grid_columnconfigure(c, weight=1)
    for c in range(10):
        selectTableFrame.grid_columnconfigure(c, weight=1)
    for c in range(10):
        informationFrame.grid_columnconfigure(c, weight=1)
#######################################################
    
    ttk.Label(informationFrame,text = f"Course : {courseText.get().upper()}" ).grid(row=0,column=0,padx=10);
    ttk.Label(informationFrame,text=f"Filename : {filenameText.get().upper()}").grid(row=1,column=0,padx=10);
#######
    searchLabel = ttk.Label(informationFrame,text="Search by ID");
    searchLabel.grid(row=0,column=3,padx=10,pady=10);
    searchEntry = ttk.Entry(informationFrame,textvariable=searchVar,width=20);
    searchEntry.grid(row = 1, column = 3 , pady=10,padx=10);
    searchEntry.bind("<KeyRelease>",lambda e : filterTreeView());
    searchEntry.grid_configure(pady=(0,10));
#######
    toCSVbtn = ttk.Button(informationFrame,text="Export to CSV", width=12,command=lambda:toCSV(getCurrentTableView()));
    toCSVbtn.grid(row=1,column=9,sticky='e',padx=20,pady=5);
    toExcelBTN = ttk.Button(informationFrame,text="Export to Excel",width=15,command=lambda:toExcel(getCurrentTableView()));
    toExcelBTN.grid(row=1,column=8,sticky='e',padx=5,pady=5);
#    toPDFbtn = ttk.Button(informationFrame,text="Export to PDF",width =15,command=lambda :toPDF(getCurrentTableView()));
#    toPDFbtn.grid(row=1,column=7,sticky='e',padx=5,pady=5);
#######
    ttk.Label(selectTableFrame,text="Table to present : " ).grid(row=0,column=0,padx=10);
    tableEntry = ttk.Entry(selectTableFrame,textvariable=tableText,width=10);
    tableEntry.grid(row=1,column=0,pady=15);
    tableEntry.bind("<Return>",lambda e : selectTable());
    ttk.Button(selectTableFrame,text="Select Table",width=15,command=selectTable).grid(row=1,column=1,padx=10);
    tableEntry.focus_set();
    global statsLabel
    statsLabel = ttk.Label(selectTableFrame,text="")
    statsLabel.grid(row=1,column=2,sticky='ew',padx=10,pady=5)
    histogramBTN = ttk.Button(selectTableFrame,text="Show Histogram",command=lambda :showHistogram(tableText.get()))
    histogramBTN.grid(row = 1 , column=9,padx=5,pady=5)
######
    ttk.Label(addFrame,text="ID:").grid(row=0,column=0,padx=5);
    global idEntry;
    global scoreEntry;
    idEntry = ttk.Entry(addFrame,textvariable=idText,width=10);
    idEntry.grid(row=0,column=1,padx=10);
    idEntry.bind("<Return>",lambda e : scoreEntry.focus_set());
    idEntry.bind("<KeyRelease>",lookupStudentName)
    ttk.Label(addFrame,text="Score:").grid(row=0,column=3,padx=5);
    scoreEntry = ttk.Entry(addFrame,textvariable=scoreText,width=10);
    scoreEntry.grid(row=0,column=4,padx=5);
    scoreEntry.bind("<Return>",lambda e : addItem());
    ttk.Button(addFrame,text="Add",width=10,command=addItem).grid(row=0,column=5,padx=5);
    ttk.Button(addFrame , text = "Update" , width = 10, command=openUpdateWindow).grid(row=0,column = 6,padx=5);
    global nameLookupLabel
    nameLookupLabel = ttk.Label(addFrame,text = "Name: ---")
    nameLookupLabel.grid(row=0,column=2,padx=5)
    main_window.bind("<Control-u>",lambda e :openUpdateWindow());
    main_window.bind("<Control-f>",lambda e: searchEntry.focus_set());
    main_window.bind("<Control-o>",lambda e : tableEntry.focus_set());
    main_window.bind("<Control-n>",lambda e : idEntry.focus_set());
    main_window.bind("<Escape>",toggleEscMenu);
######
    ttk.Label(removeFrame,text="ID to remove:").grid(row=0,column=0,padx=5);
    removeEntry = ttk.Entry(removeFrame,textvariable=removeIdText,width=10);
    removeEntry.grid(row=0,column=1,padx=5);
    removeEntry.bind("<Return>",lambda e : removeItem());
    ttk.Button(removeFrame,text="Remove",width=10,command=removeItem).grid(row=0,column=2,padx=5);
    ttk.Button(informationFrame,text = "Finalize",width=12,command=finalizeCourse).grid(row=0,column=9,padx=20,sticky='e');
######
    idText.set(""); # type: ignore
    scoreText.set(""); # type: ignore
    removeIdText.set(""); # type: ignore
######
    main_window.protocol("WM_DELETE_WINDOW", on_window_close);
################################
############# Main #############  
if __name__ == "__main__":
    openCourseWindow()
    main_window.mainloop();
################################