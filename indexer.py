""" 
Description: The script creates a faiss index from the analyze results json created with Azure AI Document Intelligence -> file variable. 
The index files are written to faiss/{{sourcename}}. The extraced tables are added to the Documents according to the corresponding pages 
"""

import json
import os
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import tablehelper as tb

def loadanalyzerjson(jsonfilepath):
    import json
    with open(jsonfilepath, encoding='utf-8') as json_file:
        data = json.load(json_file)
    
    if "analyzeResult" in data:
        data=data["analyzeResult"]
    
    print(jsonfilepath+" loaded with "+str(len(data['pages']))+" pages, "+str(len(data['paragraphs']))+" paragraphs and "+str(len(data['tables']))+" tables")
    
    string=json.dumps(data)
    string=string.replace("boundingRegions","bounding_regions")
    string=string.replace("pageNumber","page_number")
    string=string.replace("columnCount","column_count")
    string=string.replace("rowCount","row_count")
    string=string.replace("rowIndex","row_index")
    string=string.replace("columnIndex","column_index")
    string=string.replace("keyValuePairs","key_value_pairs")
    
    #writing Text to file
    txtfile=jsonfilepath+'.txt'
    print("Writing plain text to "+txtfile)
    with open(txtfile, "w", encoding='utf-8') as text_file:
        text_file.write(data['content'])    
    return json.loads(string)

def gettokens(text):
    import tiktoken
    enc = tiktoken.encoding_for_model('gpt-3.5-turbo')
    return len(enc.encode(text))


def createdocs(jsondata,maxtokensize,sourcename):
    import tablehelper as tb
    from langchain.docstore.document import Document
    data=jsondata
    spans={}
    #collect spans from tables
    for idx,tab in enumerate(data['tables']):
        if(len(tab['spans'])==1):
            key=tab['spans'][0]['offset']
            spans[str(key)]=idx
        else:
            smallesoffset=9999999999999999999999999
            for sp in tab['spans']:
                if sp['offset']<smallesoffset:
                    smallesoffset=sp['offset']
            spans[str(smallesoffset)]=idx
                    

    docs = []
    pagenr=[]
    sectionHeading=""
    mdtextlist=[]
    fullmdtext=""
    endoftable=0
    tablesearchkey=-1
    largestdoc=0
    pagecontent={}
    mdtext=""
    pagesources=[]
    for i in range(1,len(data['pages'])+1):
        pagecontent[str(i)]=""
    
    print("Creating docs for "+sourcename+" with "+str(len(data['paragraphs']))+" paragraphes and "+str(len(data['tables']))+" tables")
    #iterate over all paragraphes and create docs with mdtext seperated by sectionHeadings
    for idx,paragraphes in enumerate(data['paragraphs']):
        #when content is 7 Price conditions, then print content
        if paragraphes['spans'][0]['offset']>=endoftable:
            if 'role' in paragraphes:
                #if paragraphes['role']=='sectionHeading' check if sectionHeading is the same as before:
                if paragraphes['role']=='sectionHeading':
                    if sectionHeading!=paragraphes['content']:
                        #only create new doc if sectionHeading is not empty
                        if sectionHeading!='':
                            #build mdtext and create docs with content smaller than maxtokensize
                            mdtext="## "+sectionHeading+"\n\n"

                            #add content to pagecontent object
                            key=str(paragraphes['bounding_regions'][0]['page_number'])
                            if key in pagecontent:
                                pagecontent[key]=pagecontent[key]+"## "+paragraphes['content']+"\n\n"
                            else:
                                pagecontent[key]="## "+paragraphes['content']+"\n\n"
                                
                            pagesources = []
                            for pid,md in enumerate(mdtextlist):
                                if gettokens(mdtext+md)<=maxtokensize:
                                    mdtext=mdtext+md
                                    if pagenr[pid] not in pagesources:
                                        pagesources.append(pagenr[pid])
                                else:
                                    if (gettokens(md)>maxtokensize):
                                        tokens=gettokens(md)
                                        if tokens>largestdoc:
                                            largestdoc=tokens
                                        docs.append(Document(page_content=md, metadata={"source": sourcename, "pages":[pagenr[pid]], "tokens":tokens}))   
                                        fullmdtext=fullmdtext+md
                                    else:         
                                        tokens=gettokens(mdtext)
                                        if tokens>largestdoc:
                                            largestdoc=tokens
                                        docs.append(Document(page_content=mdtext, metadata={"source": sourcename, "pages":pagesources, "tokens":tokens}))
                                        #add to fullmdtext
                                        fullmdtext=fullmdtext+mdtext
                                        mdtext=md
                                        pagesources = [pagenr[pid]]
                            
                            #add last doc 
                            if len(pagesources)>0:
                                fullmdtext=fullmdtext+mdtext
                                tokens=gettokens(mdtext)
                                if tokens>largestdoc:
                                    largestdoc=tokens
                                docs.append(Document(page_content=mdtext, metadata={"source": sourcename, "pages":pagesources, "tokens":tokens}))

                            #reset mdtext and pagenr
                            mdtextlist=[]
                            pagenr=[]
                        #set new sectionHeading
                        sectionHeading=paragraphes['content']
                else:
                    #add paragraphes to mdtext
                    mdtextlist.append(paragraphes['content']+"\n\n")
                    page=paragraphes['bounding_regions'][0]['page_number']
                    pagenr.append(page)
                    #add content to pagecontent object
                    key=str(paragraphes['bounding_regions'][0]['page_number'])
                    if key in pagecontent:
                        pagecontent[key]=pagecontent[key]+paragraphes['content']+"\n\n"
                    else:
                        pagecontent[key]=paragraphes['content']+"\n\n"

            else:
                mdtextlist.append(paragraphes['content']+"\n\n")
                page=paragraphes['bounding_regions'][0]['page_number']
                pagenr.append(page)
                #add content to pagecontent object
                key=str(paragraphes['bounding_regions'][0]['page_number'])
                if key in pagecontent:
                    pagecontent[key]=pagecontent[key]+paragraphes['content']+"\n\n"
                else:
                    pagecontent[key]=paragraphes['content']+"\n\n"
                 
            #add pagenr if not already in list
            page=paragraphes['bounding_regions'][0]['page_number']
            pagenr.append(page)
                               
        #add subsequent table if exists
        searchkey=str(paragraphes['spans'][0]['offset']+paragraphes['spans'][0]['length']+1)
        if tablesearchkey in spans or searchkey in spans:
            i=spans[searchkey]
            mdtextlist.append("\n\n"+tb.tabletomd(data['tables'][i])+"\n\n")
            #add content to pagecontent object
            key=str(paragraphes['bounding_regions'][0]['page_number'])
            if key in pagecontent:
                pagecontent[key]=pagecontent[key]+"\n\n"+tb.tabletomd(data['tables'][i])+"\n\n"
            else:
                pagecontent[key]="\n\n"+tb.tabletomd(data['tables'][i])+"\n\n"
            if len(data['tables'][i]['spans'])>1:
                smallesoffset=9999999999999999999999999
                totallength=0
                for sp in data['tables'][i]['spans']:
                    totallength=totallength+sp['length']
                    if sp['offset']<smallesoffset:
                        key=sp['offset']
                        smallesoffset=sp['offset']
                endoftable=smallesoffset+totallength+1
                tablesearchkey=smallesoffset+totallength+1
            else:
                endoftable=data['tables'][i]['spans'][0]['offset']+data['tables'][i]['spans'][0]['length']+1
                tablesearchkey=data['tables'][i]['spans'][0]['offset']+data['tables'][i]['spans'][0]['length']+1
            page=data['tables'][i]['bounding_regions'][0]['page_number']
            pagenr.append(page)

    for pid,md in enumerate(mdtextlist):
        if gettokens(mdtext+md)<=maxtokensize:
            mdtext=mdtext+md
            if pagenr[pid] not in pagesources:
                pagesources.append(pagenr[pid])
        else:
            if (gettokens(md)>maxtokensize):
                tokens=gettokens(md)
                if tokens>largestdoc:
                    largestdoc=tokens
                docs.append(Document(page_content=md, metadata={"source": sourcename, "pages":[pagenr[pid]], "tokens":tokens}))   
                fullmdtext=fullmdtext+md
            else:
                tokens=gettokens(mdtext)
                if tokens>largestdoc:
                    largestdoc=tokens
                docs.append(Document(page_content=mdtext, metadata={"source": sourcename, "pages":pagesources, "tokens":tokens}))
                #add to fullmdtext
                fullmdtext=fullmdtext+mdtext
                mdtext=md
                pagesources = [pagenr[pid]]
    
    #add last doc 
    if len(pagesources)>0:
        #add to fullmdtext
        fullmdtext=fullmdtext+mdtext
        docs.append(Document(page_content=mdtext, metadata={"source": sourcename, "pages":pagesources, "tokens":gettokens(mdtext)}))

    print("Created "+str(len(docs))+" docs with a total of "+str(gettokens(fullmdtext))+" tokens. Largest doc has "+str(largestdoc)+" tokens.")
    return docs, pagecontent,fullmdtext

def create_embeddings(projectname,chunks,sourcename):
    embeddings = OpenAIEmbeddings(deployment="text-embedding-ada-002", chunk_size=16)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local("projects/"+projectname+'/faiss/'+sourcename+'.json')
    #vector_store = Chroma.from_documents(chunks, embeddings)
    return vector_store


def createindex(projectname,jsonfile,sourcename,maxtokensize):
    mdfile=jsonfile+'.md'
    tablemdfile=jsonfile+".tables.md"
    txtfile=jsonfile+'.txt'
    contentjsonfile=jsonfile+".pagecontent.json"
    keyvaluesjsonfile=jsonfile+".keyvalues.json"
    #delete tablemd file if exists
    if os.path.exists(tablemdfile): 
        os.remove(tablemdfile)
    #delete md file if exists
    if os.path.exists(mdfile):
        os.remove(mdfile)
    #delete txt file if exists
    if os.path.exists(txtfile):
        os.remove(txtfile)
    #delete content.json file if exists
    if os.path.exists(contentjsonfile):
        os.remove(contentjsonfile)
    #delete keyvalues.json file if exists
    if os.path.exists(keyvaluesjsonfile):
        os.remove(keyvaluesjsonfile)
        
    data=loadanalyzerjson(jsonfile)
    
    docs, pagecontent,fullmdtext=createdocs(data,maxtokensize,sourcename)

    #writing fullmd to file
    print("Writing markdown to "+mdfile)
    with open(mdfile, "w", encoding='utf-8') as text_file:
        text_file.write(fullmdtext)
    
    #writing Text to file
    print("Writing plain text to "+txtfile)
    with open(txtfile, "w", encoding='utf-8') as text_file:
        text_file.write(data['content'])
    
    #writing pagecontent to file
    with open(contentjsonfile, 'w', encoding='utf-8') as outfile:
        json.dump(pagecontent, outfile, indent=4)
    print(contentjsonfile+" created")    
    
    mdtext=""
    for tabid, tab in enumerate(data['tables']):
        mdtext=mdtext+"## Table "+str(tabid)+" from page "+str(tab['bounding_regions'][0]['page_number'])+"\n"+tb.tabletomd(tab)+"\n"

    keyvalues={}
    for i in range(1,len(data['pages'])+1):
        keyvalues[str(i)]={}
    #create keyvalues json
    for keyvalue in data['key_value_pairs']:
            pagekey=str(keyvalue['key']['bounding_regions'][0]['page_number'])
            if 'value' in keyvalue:
                if keyvalue['value'] is not None:
                    keyvalues[pagekey][keyvalue['key']['content']]=keyvalue['value']['content']
            
    #writing keyvalues to file
    with open(keyvaluesjsonfile, 'w', encoding='utf-8') as outfile:
        json.dump(keyvalues, outfile, indent=4)

    #writing to file
    with open(tablemdfile, "w", encoding='utf-8') as text_file:
        text_file.write(mdtext)
    print(tablemdfile+" created")
   
    print("Total Nr of Docs: "+str(len(docs)))
   
    print("Creating FAISS Vector Store")
    create_embeddings(projectname,docs,sourcename)
    print("Done")

    return sourcename+'.json'
 
if __name__ == "__main__":       
    import os
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=True)
    os.environ["OPENAI_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]
    os.environ["OPENAI_API_KEY"] = os.environ["AZURE_OPENAI_API_KEY"]
    os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]
    os.environ["OPENAI_API_TYPE"] = "azure"
    
    
    source="DWS Annual Report 2022_EN.pdf"
    #load json file
    
    file="projects/dws/files/source.json"
    print("Source: "+source)
    print("Loading JSON File")
            
    createindex(file,source,debug=False,minchar=10,calculate_tokens=True)
