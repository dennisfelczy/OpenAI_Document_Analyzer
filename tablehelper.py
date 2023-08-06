
def tableinfo(tables):
    for table_idx, table in enumerate(tables):  
        print(  
            "Table # {} from page # {} has {} rows and {} columns".format(  
            table_idx, table['bounding_regions'][0]['page_number'],table['row_count'], table['column_count']  
            )  
        )  


def tabletomd(table):
    
    celldict = {}
    lastcolumn=table['column_count']-1
    
    for cell in table['cells']:
        key=str(cell['row_index'])+"-"+str(cell['column_index'])
        celldict[key]=cell['content']
    
    tsvtable=""
    for row in range(table['row_count']):
        for col in range(table['column_count']):
            key=str(row)+"-"+str(col)
            if col==0:
                tsvtable+='|'
            if key in celldict:
                tsvtable+=celldict[key]+'|'
            else:
                tsvtable+='|'
            if col==lastcolumn:
                tsvtable+='\n'
                if row==0:
                    tsvtable+='|'
                    for col in range(table['column_count']):
                        tsvtable+='---|'
                    tsvtable+='\n'
                    
    return tsvtable

def gettablesfrompage(tables, page):
    tableslist=[]
    for table_idx, table in enumerate(tables):  
        if table['bounding_regions'][0]['page_number'] == page:
            df=tabletomd(table)
            tableslist.append(df)
    return tableslist