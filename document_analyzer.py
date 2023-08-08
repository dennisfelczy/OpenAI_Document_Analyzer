'''
Description: This file contains the code for the streamlit chatbot with documents. 
The answer can be read out loud via text to speech.

run the app within the directory:
conda activate ./.conda
streamlit run ./document_analyter.demo.py

'''
import os
import streamlit as st
# loading the OpenAI api key from .env
from dotenv import load_dotenv, find_dotenv
from helperfunctions import *

import os
from langchain.embeddings.openai import OpenAIEmbeddings
#from langchain.vectorstores import Chroma
from langchain.vectorstores import FAISS
import azure.cognitiveservices.speech as speechsdk
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
import streamlit as st
import ftfy
import azure.cognitiveservices.speech as speechsdk

if 'priorproject' not in st.session_state:
    st.session_state.priorproject=''

if 'language' not in st.session_state:
    st.session_state.language='en-US'

load_dotenv(find_dotenv(), override=True)
os.environ["OPENAI_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]
os.environ["OPENAI_API_KEY"] = os.environ["AZURE_OPENAI_API_KEY"]
os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]
os.environ["OPENAI_API_TYPE"] = "azure"
speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
speech_config.speech_recognition_language=st.session_state.language
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
if 'project' not in st.session_state:
    refresh_project_list()


# Set Vector list
if 'vector_index_list' not in st.session_state  and 'project' in st.session_state:
    refresh_vector_index_list()

if 'k' not in st.session_state:    
    st.session_state.k=1


if 'topic_list' not in st.session_state:
    refresh_topic_list()

if len(st.session_state.topic_list)>0:
    if 'topic' not in st.session_state:
        st.session_state.topic = st.session_state.topic_list[0]
    

if len(st.session_state.topic_list)>0:
    if 'query_list' not in st.session_state:
        load_topic()

if 'vector_index_list' not in st.session_state and 'project' in st.session_state:
    refresh_vector_index_list()


if os.path.isfile("projects/"+st.session_state.project+"/logo.png"):
    st.image("projects/"+st.session_state.project+'/logo.png')    
else:
    st.image('img.png')        

st.subheader('Azure OpenAI - Document Analyzer')
if 'document_name' not in st.session_state:
    st.session_state.document_name = ''

with st.sidebar:
    with st.container():
        st.subheader("Project")
        with st.expander("Edit Projects"):
            with st.form(key="Add new project",clear_on_submit=True):
                new_project_name=st.text_input('New Project Name')
                col1,col2 = st.columns([1,1])
                with col1:
                    submitted = st.form_submit_button("Add project")
                with col2:
                    del_project = st.form_submit_button('Delete project')
                if del_project:
                    delete_project(st.session_state.project)
                if submitted:
                    add_project(new_project_name)
        st.selectbox('Select project', st.session_state.project_list,key='project',label_visibility="hidden")
    if 'project' in st.session_state and st.session_state.project != st.session_state.priorproject:
        loadproject()
        st.session_state.priorproject=st.session_state.project
                   
    if(len(st.session_state.project_list)>0):
        with st.container():
            st.subheader("Document")
            with st.expander("Add new Document"):
                # file uploader widget
                uploaded_file = st.file_uploader('Upload a file:', type=['pdf'])

                # token size number widget
                token_size = st.number_input('Token size:', min_value=128, max_value=1024, value=512)
                
                # add data button widget
                analyze = st.button('Analyze with Azure AI Document Intelligence and create Vector Index')

                if analyze and uploaded_file:
                    jsonfilename = "projects/"+st.session_state.project+'/files/'+uploaded_file.name+'.json'
                    if os.path.isfile(jsonfilename):
                        print('JSON File '+jsonfilename+' already exists. Skipping Analysis.')
                    else:
                        with st.spinner('Analyzing '+uploaded_file.name+' with Azure AI Document Intelligence...'):
                        
                            #get full path of uploaded file 
                            bytes_data = uploaded_file.read()
                            file_name = os.path.join("projects/"+st.session_state.project+'/files/', uploaded_file.name)
                            with open(file_name, 'wb') as f:
                                f.write(bytes_data)
                            
                            from analyzer import analyze_general_documents as di
                            jsonfilename = di(st.session_state.project,uploaded_file.name)
                            st.success('JSON File '+jsonfilename+' created successfully.')
                            
                    with st.spinner('Reading, chunking and embedding Document Intelligence Results from '+uploaded_file.name+'...'):   
                        from indexer import createindex as ci
                        st.session_state.vector_index_name=ci(st.session_state.project,jsonfilename,uploaded_file.name,token_size)
                        load_embeddings()
                        refresh_vector_index_list()
                        st.success('Document Intelligence Results chunked and embedded. Vector store '+ st.session_state.document_name+' created successfully.')
            st.selectbox('Select Document',st.session_state.vector_index_list ,index=0,key="vector_index_name",on_change=load_embeddings)
            

        if len(st.session_state.vector_index_list)>0:    
            with st.container():
                st.subheader("Topic")
                with st.expander("Edit Topics"):
                    with st.form(key="Add new Topic",clear_on_submit=True):
                        new_topic_name=st.text_input('New Topic Name')
                        col1,col2 = st.columns([1,1])
                        with col1:
                            submitted = st.form_submit_button("Add Topic")
                        with col2:
                            del_topic = st.form_submit_button('Delete Topic')
                        if del_topic:
                            delete_topic(st.session_state.topic)
                        if submitted:
                            add_topic(new_topic_name)
                st.selectbox('Select Topics', st.session_state.topic_list,key="topic",on_change=load_topic)
                if len(st.session_state.topic_list)>0:    
                    with st.form(key="Ground Truth",clear_on_submit=True):
                        col61,col62 = st.columns([2,1])
                        with col61:
                            ground_truth=st.text_input('Pages to check against:',key="ground_truth",value=str(",".join(str(x) for x in getgroundtruthpages())))
                        with col62:
                            st.form_submit_button("Add Ground Truth",on_click=setgroundtruthpages)


if 'vs' not in st.session_state:
    load_embeddings()
    

if(len(st.session_state.topic_list)>0):
    tab1, tab2,tab3 = st.tabs(["Document Viewer","Context Queries","Question Answering"])

    #Tab 1: Document Viewer
    with tab1:
        col1, col2,col3,col4,col5 = st.columns([2.8,0.8,1.2,1,1])    
        with col1:
            col21, col22 = st.columns([1,1])
            with col21:
                startpage=st.number_input('Start Page',min_value=1, max_value=1000,key="startpage")
            with col22:
                endpage=st.number_input('End Page',min_value=1, max_value=1000,key="endpage")
        with col2:
            show=st.button('Show Pages')
        with col3:
            fulldocument=st.button('Full document',on_click=resetpage)       
        with col4:
            tables=st.button('Show tables')
        with col5:
            keyvalues=st.button('Show Key Values')
        if tables:
            with st.expander("Tables",expanded=True):
                if 'tables' in st.session_state:
                    st.markdown(st.session_state.tables)
        if keyvalues:
            with st.expander("Key Values",expanded=True):
                if 'keyvalues' in st.session_state:
                    st.json(st.session_state.keyvalues)
        if show or fulldocument:
            if fulldocument:
                startpage=1
                endpage=len(st.session_state.pagecontent)
            for i in range(startpage,endpage):
                if i==1:
                    st.markdown('***Begin of Document***')
                st.markdown(ftfy.fix_encoding(st.session_state.pagecontent[str(i)]))
                st.markdown('***Page '+str(i)+' of '+str(len(st.session_state.pagecontent))+'***')
                if i==len(st.session_state.pagecontent)-1:
                    st.markdown('***End of Document***')
            if startpage==endpage:
                if startpage==1:
                    st.markdown('***Begin of Document***')
                st.markdown(ftfy.fix_encoding(st.session_state.pagecontent[str(startpage)]))
                st.markdown('***Page '+str(startpage)+' of '+str(len(st.session_state.pagecontent))+'***')
                if endpage==len(st.session_state.pagecontent):
                    st.markdown('***Begin of Document***')

                
    #Tab 2: Context Queries
    with tab2:
        col1,col2,col5 = st.columns([0.2,2,0.4])
        with col1:
            stt = st.button(':studio_microphone:',key="stt")
        with col2:
            with st.form(key="Add new Query",clear_on_submit=True):
                col3,col4 = st.columns([3.4,1])
                with col3:
                    new_query_name=st.text_input('New Query',label_visibility='collapsed')
                with col4:
                    # k number input widget
                    add_query_button = st.form_submit_button("Add Query")
        if stt:
            st.info("Speak into your microphone.")
            speech_recognition_result = speech_recognizer.recognize_once_async().get()
            if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print("Recognized: {}".format(speech_recognition_result.text))
                add_query(speech_recognition_result.text)   
                st.session_state.query=speech_recognition_result.text
            elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
                st.warning("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
            elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speech_recognition_result.cancellation_details
                st.warning("Speech Recognition canceled: {}".format(cancellation_details.reason))
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    st.warning("Error details: {}".format(cancellation_details.error_details))
                    
        if add_query_button:
            add_query(new_query_name)      
            st.session_state.query = new_query_name
            getcontext()
        with col5:
            st.session_state.k=st.number_input('k',value=1,min_value=1, max_value=20,)   
        st.text("List of stored context queries:")
        col1,col2= st.columns([3.35,1])  
        with col1:
            st.selectbox('Select a Query',st.session_state.query_list ,index=0,label_visibility='collapsed',key="query")
        with col2:
            col91,col92 = st.columns([1,1])
            with col91:
                run_query=st.button('Query')
            with col92:
                del_query = st.button('Delete',on_click=delete_query)
        if run_query or stt:
            getcontext()
            
        if 'context' in st.session_state:
            with st.expander("Query Results",expanded=False):
                for i,content in enumerate(st.session_state.querycontent):
                    st.header('Result from page '+st.session_state.querypages[i]+" with score "+str(st.session_state.queryscores[i])+":")
                    st.markdown(content)
            with st.expander(st.session_state.reducedpages,expanded=True):
                st.header('Query: ')
                st.markdown(st.session_state.query)
                st.header('Pages according to Similarity Search: ')
                st.markdown(st.session_state.context)
            
    #Tab 3: Question Answering         
    with tab3:
        col81, col82,col83 = st.columns([1, 1,1])
        with col81:
            enable_tts=st.checkbox('Text to Speech')
            # Select language
            st.session_state.language = st.selectbox('Select language',("en-US", "de-DE"),index=0,label_visibility='collapsed')
        with col82:
            st.session_state.model = "gpt-35-turbo" #st.selectbox('Model',("gpt-35-turbo","text-davinci-003"),index=0)
            st.markdown("**Model:**")
            st.write(st.session_state.model)
        with col83:    
            # t number input widget
            st.session_state.t = st.number_input('Temperature', min_value=0.0, max_value=1.0, value=0.0)
        
        #q = st.text_input('Ask a question about the content of your file: '+st.session_state.document_name,key="questionwidget")
        # user's question text input widget
        col200,col201 = st.columns([0.4,5])
        with col200:
            stt2 = st.button(':studio_microphone:',key="stt2")
        with col201:
            with st.form(key="Add new Question",clear_on_submit=True):
                col203,col204 = st.columns([3.9,1])
                with col203:
                    new_question_name=st.text_input('New Question',label_visibility='collapsed')
                with col204:
                    # k number input widget
                    add_question_button = st.form_submit_button("Add Question")
        if stt2:
            st.info("Speak into your microphone.")
            speech_recognition_result = speech_recognizer.recognize_once_async().get()
            if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print("Recognized: {}".format(speech_recognition_result.text))
                add_question(speech_recognition_result.text)      
                st.session_state.question=speech_recognition_result.text
            elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
                st.warning("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
            elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speech_recognition_result.cancellation_details
                st.warning("Speech Recognition canceled: {}".format(cancellation_details.reason))
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    st.warning("Error details: {}".format(cancellation_details.error_details))
                    
        if add_question_button:
            add_question(new_question_name)      
            st.session_state.question = new_question_name
            askquestion()
        st.text("List of stored questions:")
        col111,col112= st.columns([3.8,1])  
        with col111:
            st.selectbox('Select a Question',st.session_state.question_list ,index=0,label_visibility='collapsed',key="question")
        with col112:
            col191,col192 = st.columns([0.8,1.1])
            with col191:
                run_question=st.button('Ask')
            with col192:
                del_question = st.button('Delete',on_click=delete_question,key="delquestion")
        if run_question or stt2:
            askquestion()
            
        if 'answer' in st.session_state:
            st.header('Question: ')
            st.markdown(st.session_state.question)
            # text area widget for the LLM answer
            #st.text_area('Azure OpenAI Answer: ', value=answer,height=200)
            st.header('Azure OpenAI Answer: ')
            with st.container():
                st.markdown(st.session_state.answer)
                sourcetext="Source: "+st.session_state.vector_index_name+" - Pages:"+str(",".join(str(x) for x in st.session_state.sourcepages))
            if enable_tts:
                synthesize_text(st.session_state.answer)
            st.divider()

            with st.expander(sourcetext):
                counter=1
                st.header('Sources:')
                for page in st.session_state.sourcepages:
                    st.divider()
                    st.write("Source: "+st.session_state.document_name+" - Page:"+str(page))
                    st.divider()
                    st.markdown(ftfy.fix_encoding(st.session_state.pagecontent[str(page)]))
                    counter=counter+1




