from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import pipeline
import uvicorn

app = FastAPI(title="Smart Helpdesk Bot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str

vectorstore = None
qa_pipeline = None

def initialize_vectorstore():
    """Initialize or load the vector store with documents"""
    global vectorstore
    docs_path = os.path.join(os.path.dirname(__file__), "..", "docs")
    
    if os.path.exists(docs_path):
        print("Loading documents and creating vector store...")
        
        # Load documents from the docs folder
        loader = DirectoryLoader(docs_path, glob="**/*.txt", loader_cls=TextLoader)
        documents = loader.load()
        
        if not documents:
            print("No documents found in docs folder. Creating empty vector store.")
            # Create empty vector store
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectorstore = Chroma(
                persist_directory="./chroma_db",
                embedding_function=embeddings
            )
            return
        
        print(f"Loaded {len(documents)} documents")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
        texts = text_splitter.split_documents(documents)
        
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Create vector store
        vectorstore = Chroma.from_documents(
            documents=texts,
            embedding=embeddings,
            persist_directory="./chroma_db"
        )
        
        print(f"Created vector store with {len(texts)} document chunks")
    else:
        print("Docs folder not found. Creating empty vector store.")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embeddings
        )

def initialize_qa_pipeline():
    """Initialize the question-answering pipeline"""
    global qa_pipeline
    print("Loading question answering model...")
    qa_pipeline = pipeline(
        "question-answering",
        model="distilbert-base-uncased-distilled-squad",
        tokenizer="distilbert-base-uncased-distilled-squad"
    )
    print("Question answering model loaded")

@app.on_event("startup")
async def startup_event():
    """Initialize AI components on startup"""
    initialize_vectorstore()
    initialize_qa_pipeline()

@app.get("/")
async def root():
    return {"message": "Smart Helpdesk Bot API is running"}

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Process questions using RAG pipeline"""
    try:
        if vectorstore is None or qa_pipeline is None:
            raise HTTPException(status_code=500, detail="System not properly initialized")
        
        # Search for relevant documents
        docs = vectorstore.similarity_search(request.question, k=3)
        
        if not docs:
            return AnswerResponse(answer="No relevant documents found for your question. Please contact IT support for assistance.")
        
        # Combine document content as context, removing duplicates
        context_parts = []
        seen_content = set()
        for doc in docs:
            if doc.page_content not in seen_content:
                context_parts.append(doc.page_content)
                seen_content.add(doc.page_content)
        
        context = " ".join(context_parts)
        
        print(f"Question: {request.question}")
        print(f"Context: {context[:200]}...")
        
        # Use the QA pipeline to answer the question
        result = qa_pipeline(question=request.question, context=context)
        
        # Extract the answer
        answer = result["answer"]
        
        # If the answer is too short or generic, provide more context
        if len(answer) < 50:
            # Fallback: return relevant document content directly
            answer = f"Based on our documentation:\n\n{context}"
        
        # Add confidence score if available
        if "score" in result:
            confidence = result["score"]
            print(f"Confidence: {confidence}")
            if confidence < 0.3:
                answer = f"Based on our documentation:\n\n{context}"
        
        return AnswerResponse(answer=answer)
        
    except Exception as e:
        print(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)