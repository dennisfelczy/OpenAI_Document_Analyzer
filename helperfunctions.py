import os
from langchain.embeddings.openai import OpenAIEmbeddings
#from langchain.vectorstores import Chroma
from langchain.vectorstores import FAISS
import azure.cognitiveservices.speech as speechsdk
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
import json
import shutil
import streamlit as st
import ftfy

# refresh vector index list from directory names in faiss folder
def refresh_vector_index_list():
    print(st.session_state.project)
    directory_list = list()
    for root, dirs, files in os.walk("projects/"+st.session_state.project+"/faiss/", topdown=False):
        for name in dirs:
            directory_list.append(os.path.join(name))
    st.session_state.vector_index_list = directory_list


def resetpage():
    st.session_state.startpage=1
    st.session_state.endpage=len(st.session_state.pagecontent)

# refresh vector index list from directory names in faiss folder
def refresh_topic_list():
    directory_list = list()
    for root, dirs, files in os.walk("projects/"+st.session_state.project+"/topics/", topdown=False):
        for name in dirs:
            directory_list.append(os.path.join(name))
    st.session_state.topic_list = directory_list

def add_topic(topicname):
    print('adding topic to '+st.session_state.project)
    if os.path.isdir("projects/"+st.session_state.project+"/topics/"+topicname):
        st.error("Topic already exists")
    else:
        os.mkdir("projects/"+st.session_state.project+"/topics/"+topicname)
        #write questions.txt to dir
        with open("projects/"+st.session_state.project+"/topics/"+topicname+"/questions.txt", "w") as f:
            pass
        #write queries.txt to dir
        with open("projects/"+st.session_state.project+"/topics/"+topicname+"/queries.txt", "w") as f:
            pass
        #write ground_truth.txt to dir
        with open("projects/"+st.session_state.project+"/topics/"+topicname+"/ground_truth.txt", "w") as f:
            pass
    refresh_topic_list()
    st.session_state.topic=topicname
    load_topic()  


def delete_topic(topicname):
    if os.path.isdir("projects/"+st.session_state.project+"/topics/"+topicname):
        #delete directory
       shutil.rmtree("projects/"+st.session_state.project+"/topics/"+topicname, ignore_errors=True)
    refresh_topic_list()
    if(len(st.session_state.topic_list)>0):
        st.session_state.topic=st.session_state.topic_list[0]
        load_topic()     
        
def refresh_project_list():
    if 'project_list' in st.session_state:
        del st.session_state.project_list
    dirs = [entry.path for entry in os.scandir('projects') if entry.is_dir()]
    #replace "projects\\" with " 
    for i in range(len(dirs)):
        dirs[i]=dirs[i].replace("projects\\","")
    st.session_state.project_list = dirs
    if(len(dirs)>0):
        st.session_state.project=dirs[0]

def add_project(projectname):
    if os.path.isdir("projects/"+projectname):
        st.error("project already exists")
    else:
        os.mkdir("projects/"+projectname)
        #write questions.txt to dir
        os.mkdir("projects/"+projectname+"/files")
        os.mkdir("projects/"+projectname+"/faiss")
        os.mkdir("projects/"+projectname+"/topics")
    refresh_project_list()
    st.session_state.project=projectname
    loadproject()



def delete_project(projectname):
    if os.path.isdir("projects/"+projectname):
        #delete directory
       shutil.rmtree("projects/"+projectname, ignore_errors=True)
    refresh_project_list()
    if(len(st.session_state.project_list)>0):
        st.session_state.project=st.session_state.project_list[0]
        loadproject()
        

# refresh vector index list from directory names in faiss folder
def refresh_vector_index_list(): 
    directory_list = list()
    for root, dirs, files in os.walk("projects/"+st.session_state.project+"/faiss/", topdown=False):
        for name in dirs:
            directory_list.append(os.path.join(name))
    st.session_state.vector_index_list = directory_list

def setquestion():
    if(st.session_state['question']!="-"):
        st.session_state['questioninput']=st.session_state['question']

def getmessages(systemessage,question):
    from langchain.schema import(
    HumanMessage,
    SystemMessage
    )
    messages = [
    SystemMessage(content=systemessage),
    HumanMessage(content=question)
    ]
    return messages
    
# Speech to Text with Azure Cognitive Services
def recognize_from_microphone(target):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION" which are loaded from the .env file in main
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
    speech_config.speech_recognition_language=st.session_state.language

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    st.info("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
        if target=="question":
            add_question(speech_recognition_result.text)      
            st.session_state.question=speech_recognition_result.text
        else:
            add_query(speech_recognition_result.text)   
            st.session_state.query=speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")

def askquestion():
    if 'context' not in st.session_state:
        st.warning('No Context is used. Please use query first')
    else:
        if 'vs' in st.session_state: # if there's the vector store (user uploaded, split and embedded a file)
            #replace â‚¬ with € in the answer
            st.session_state.answer=ftfy.fix_encoding(askwithcontext(st.session_state.question))
        else:
            st.error('Please select a Document first')


def gettokens(text):
    import tiktoken
    enc = tiktoken.encoding_for_model('gpt-3.5-turbo')
    return len(enc.encode(text))

# Text to Speech with Azure Cognitive Services
# This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
def synthesize_text(text):
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    # The language of the voice that speaks.
    
    if st.session_state.language=="de-DE":
        speech_config.speech_synthesis_voice_name='de-DE-KatjaNeural'
    else:
        speech_config.speech_synthesis_voice_name='en-US-JennyNeural'
    
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text")
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

def load_embeddings():
    embeddings = OpenAIEmbeddings(deployment="text-embedding-ada-002", chunk_size=16)
    st.session_state.vs = FAISS.load_local("projects/"+st.session_state.project+"/faiss/"+st.session_state.vector_index_name, embeddings)
    st.session_state.document_name = st.session_state.vector_index_name
    st.success(st.session_state.vector_index_name+' loaded successfully.')
    contentjsonfile="projects/"+st.session_state.project+"/files/"+st.session_state.vector_index_name+".pagecontent.json"
    with open(contentjsonfile, encoding='utf-8') as json_file:
        st.session_state.pagecontent = json.load(json_file)
    #st.success('Pagecontent '+ st.session_state.vector_index_name+' loaded successfully.')
    tablemdfile="projects/"+st.session_state.project+"/files/"+st.session_state.vector_index_name+".tables.md"
    with open(tablemdfile, encoding='utf-8') as table_file:
            st.session_state.tables = table_file.read()
    fullmdfile="projects/"+st.session_state.project+"/files/"+st.session_state.vector_index_name+".md"
    with open(fullmdfile, encoding='utf-8') as fullmd_file:
        st.session_state.fullmd = fullmd_file.read()   
    keyvaluesjsonfile="projects/"+st.session_state.project+"/files/"+st.session_state.vector_index_name+".keyvalues.json"
    with open(keyvaluesjsonfile, encoding='utf-8') as json_file:
        st.session_state.keyvalues = json.load(json_file)
    #st.success('Tables from '+ st.session_state.vector_index_name+' loaded successfully.')
    st.session_state.startpage=1
    resetpage()

def getgroundtruthpages():
    groundtruthpages = []
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/ground_truth.txt') as f:
        for line in f:
            if line.split(";")[0] == st.session_state.vector_index_name:
                groundtruthpages=line.split(";")[1].split(",")
                for i in range(len(groundtruthpages)):
                    groundtruthpages[i]=int(groundtruthpages[i])
            #print(groundtruthpages)
    return groundtruthpages


def setgroundtruthpages():
    newgroundtruthpages = st.session_state.ground_truth
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/ground_truth.txt','r') as f:
        lines = f.readlines()

    addline=True
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/ground_truth.txt','w') as f:
        for line in lines:
            if line.split(";")[0] == st.session_state.vector_index_name:
                addline=False
                if newgroundtruthpages=="\n":
                    f.write(st.session_state.vector_index_name+";"+newgroundtruthpages+"\n")
            else:
                f.write(line)
    if addline:
        with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/ground_truth.txt','a') as f:
            f.write(st.session_state.vector_index_name+";"+newgroundtruthpages+"\n")
    


def getcontext():
    if st.session_state.query!="-":
        vector_store = st.session_state.vs
        query = st.session_state.query
        groundtruthpages=getgroundtruthpages()
        pagecontent=st.session_state.pagecontent
        k=st.session_state.k
        from langchain.embeddings.openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(deployment="text-embedding-ada-002", chunk_size=16)

        pagechecker=[]

        print("Query: ",query)    
        result= vector_store.similarity_search_with_score(query=query, k=k, embeddings=embeddings, return_metadata=True)
        pages=[]
        context=""
        querycontent=[]
        queryscores=[]
        querypages=[]
        for r in result:
            querycontent.append(r[0].page_content)
            queryscores.append(r[1])
            querypages.append(str(",".join(str(x) for x in r[0].metadata['pages'])))
            for pagenr in r[0].metadata['pages']:
                if pagenr not in pages:
                    pages.append(pagenr)
        sortedpages=pages.copy()
        sortedpages.sort()
        
        for p in sortedpages:
            currenttokens=gettokens(context)
            if gettokens(context+pagecontent[str(p)])<=3500:
                context+=pagecontent[str(p)]
            else:
                st.info("Warning !!! Skipping page "+str(p)+" as context is already "+str(currenttokens))
                print("Warning !!! Skipping page "+str(p)+" as context is already "+str(currenttokens))

        st.session_state.context=context
        st.session_state.sourcepages=pages
        st.session_state.querycontent=querycontent
        st.session_state.queryscores=queryscores
        st.session_state.querypages=querypages
        if len(groundtruthpages)>0:
            st.info("expected pages: "+str(",".join(str(x) for x in groundtruthpages))+" - found pages: "+str(",".join(str(x) for x in pages))+" with "+str(k)+" Sources (k) and a context size of "+str(gettokens(context))+" tokens")
        else:
            st.info("found pages: "+str(",".join(str(x) for x in pages))+" with "+str(k)+" Sources (k) and a context size of "+str(gettokens(context))+" tokens")
        print("expected pages: ",groundtruthpages," - found pages: ",pages," with ",k," Sources (k) amd a context size of ",gettokens(context)," tokens")
        st.session_state.reducedpages=str(str(len(pages)))+" of "+str(len(st.session_state.pagecontent))+" pages ("+str(((len(pages)/len(st.session_state.pagecontent)))*100)+"%)"
        allpagesfound=True
        
        if len(groundtruthpages)>0:       
            for gtp in groundtruthpages:
                if gtp not in pages:
                    allpagesfound=False
                    st.warning("missing page: "+str(gtp)+" - try a higher k value or refine query")
                    print("missing page: ",gtp)
            if allpagesfound:
                st.success("all pages found. Document reduced from "+str(len(st.session_state.pagecontent))+" to "+str(len(pages))+" pages ("+str((1-(len(pages)/len(st.session_state.pagecontent)))*100)+"%)")
                print("all pages found")
            st.session_state.questioninput=st.session_state.question
        else:
            st.info("No pages for Ground Truth check defined")
        
def askwithcontext(question):
    from langchain.llms import AzureOpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chat_models import AzureChatOpenAI
    vector_store = st.session_state.vs
    context=st.session_state.context
    t=st.session_state.t
    
    #text davinci
    if st.session_state.model=="text-davinci-003":

        prompttemplate = PromptTemplate(
            input_variables=["context", "question"], 
            template= """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. If you use information which were not part of the context remove them from the answer.

            Context:
            {context}

            Question: {question}
            Helpful Answer:"""
        )
        
        
        prompt=prompttemplate.format(context=context, question=question)
        llm = AzureOpenAI(deployment_name='text-davinci-003', temperature=t)
        answer=llm(prompt)
    #GPT-35-Turbo        
    if st.session_state.model=="gpt-35-turbo":

        prompttemplate = PromptTemplate(
            input_variables=["context"], 
            template= """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. If you use information which were not part of the context remove them from the answer.

            Context:
            {context}
            
            """
        )
        
        prompt=prompttemplate.format(context=context)
        
        chat=AzureChatOpenAI(deployment_name='gpt-35-turbo', temperature=t)
        answer=chat(getmessages(prompt,question)).content
        
    return answer

def delete_query():
    queryname=st.session_state.query
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/queries.txt', 'r') as f:
        lines = f.readlines()

    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/queries.txt', 'w') as f:
        for line in lines:
            if line.strip("\n") != queryname:
                f.write(line)
                #print(line)
    load_topic(False)
    if 'context' in st.session_state:
        del st.session_state.context

                                
def add_query(queryname):
    #add query to end of queries.txt
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/queries.txt', 'a') as f:
        f.write(queryname+"\n")
    load_topic(False)

def delete_question():
    questionname=st.session_state.question
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/questions.txt', 'r') as f:
        lines = f.readlines()

    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/questions.txt', 'w') as f:
        for line in lines:
            if line.strip("\n") != questionname:
                f.write(line)
                #print(line)
    load_topic(False)
    if 'answer' in st.session_state:
        del st.session_state.answer

                                
def add_question(questionname):
    #add question to end of questions.txt
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/questions.txt', 'a') as f:
        f.write(questionname+"\n")
    load_topic(False)


def load_topic(reset=True):
    if reset:
        if 'context' in st.session_state:
            del st.session_state.context
        if 'answer' in st.session_state:
            del st.session_state.answer
    #open queries text and add all lines to a list
    query_list = []
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/queries.txt') as f:
        for line in f:
            query_list.append(line.strip())
    st.session_state.query_list = query_list
    #open questions text and add all lines to a list
    question_list = []
    with open("projects/"+st.session_state.project+'/topics/'+st.session_state.topic+'/questions.txt') as f:
        for line in f:
            question_list.append(line.strip())
    st.session_state.question_list = question_list

    
    
def loadproject():
    if 'context' in st.session_state:
        del st.session_state.context
    if 'answer' in st.session_state:
        del st.session_state.answer
    if 'vector_index_list' in st.session_state:
        del st.session_state.vector_index_list
    if 'topic_list' in st.session_state:
        del st.session_state.topic_list
    if 'vector_index_name' in st.session_state:
        del st.session_state.vector_index_name
    if 'topic_list' in st.session_state:
        del st.session_state.topic_list
    refresh_vector_index_list()
    refresh_topic_list()
    if len(st.session_state.topic_list)>0:
        st.session_state.topic=st.session_state.topic_list[0]
        load_topic()
        #load_embeddings()

    
    
