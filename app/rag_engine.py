# rag_engine.py

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_community.llms import GigaChat
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import re
import os


def _clean_text(text: str) -> str:
    """Удаляет суррогаты и некорректные unicode-символы."""
    if not isinstance(text, str):
        return text
    return re.sub(r'[\ud800-\udfff]', '', text)


class ConstitutionDocumentProcessor:
    """Обработка и чанкинг Конституции РФ"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def _is_valid_text(self, text) -> bool:
        """Проверяет валидность текста"""
        if not text or not isinstance(text, str):
            return False
        if len(text.strip()) < 10:
            return False
        try:
            text.encode('utf-8')
            return True
        except UnicodeEncodeError:
            return False

    def _split_articles(self, text: str) -> list:
        """Разделяет текст на статьи"""
        article_positions = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if re.match(r'^Статья\s+\d+', line.strip()):
                article_positions.append((i, line.strip()))

        articles = []

        # Преамбула
        if article_positions:
            first_article_line = article_positions[0][0]
            preamble = '\n'.join(lines[:first_article_line]).strip()
            if self._is_valid_text(preamble):
                articles.append({
                    'title': 'Преамбула',
                    'content': preamble,
                    'number': '0'
                })

        # Статьи
        for i, (line_num, title) in enumerate(article_positions):
            article_match = re.search(r'Статья\s+(\d+)', title)
            article_num = article_match.group(1) if article_match else str(i + 1)

            next_line_num = article_positions[i + 1][0] if i + 1 < len(article_positions) else len(lines)
            content_lines = lines[line_num:next_line_num]
            content = '\n'.join(content_lines).strip()

            if self._is_valid_text(content):
                articles.append({
                    'title': f'Статья {article_num}',
                    'content': content,
                    'number': article_num
                })

        return articles

    def create_documents(self) -> list:
        """Создает документы с метаданными"""
        loader = TextLoader(self.file_path, encoding="utf-8")
        documents = loader.load()
        full_text = documents[0].page_content

        articles = self._split_articles(full_text)
        docs = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

        for article in articles:
            if len(article['content']) > 1500:
                chunks = text_splitter.split_text(article['content'])
                for i, chunk in enumerate(chunks):
                    if self._is_valid_text(chunk):
                        doc = Document(
                            page_content=_clean_text(chunk),
                            metadata={
                                "article": _clean_text(article['title']),
                                "article_number": article['number'],
                                "part": i + 1 if len(chunks) > 1 else None
                            }
                        )
                        docs.append(doc)
            else:
                if self._is_valid_text(article['content']):
                    doc = Document(
                        page_content=_clean_text(article['content']),
                        metadata={
                            "article": _clean_text(article['title']),
                            "article_number": article['number']
                        }
                    )
                    docs.append(doc)

        # Финальная фильтрация
        filtered_docs = [doc for doc in docs if self._is_valid_text(doc.page_content)]
        return filtered_docs


class QdrantManager:
    """Управление Qdrant коллекцией"""

    def __init__(self, host: str, port: int, collection_name: str):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port)

    def recreate_collection(self):
        """Пересоздает коллекцию"""
        try:
            self.client.delete_collection(self.collection_name)
        except:
            pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

    def upload_documents(self, documents: list, embedding_model):
        """Загружает документы в коллекцию"""
        Qdrant.from_documents(
            documents=documents,
            embedding=embedding_model,
            collection_name=self.collection_name,
            url=f"http://{self.host}:{self.port}",
            force_recreate=True
        )


class ConstitutionRAG:
    """Основной RAG движок"""

    def __init__(self, giga_credentials: str, qdrant_host: str, qdrant_port: int):
        self.giga_credentials = giga_credentials
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = "constitution_rf"
        self.embedding_model = None
        self.vectorstore = None
        self.qa_chain = None

    def initialize(self, documents: list):
        """Инициализирует весь RAG движок"""
        self.embedding_model = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

        qdrant_manager = QdrantManager(self.qdrant_host, self.qdrant_port, self.collection_name)
        qdrant_manager.recreate_collection()
        qdrant_manager.upload_documents(documents, self.embedding_model)

        self.vectorstore = Qdrant(
            client=QdrantClient(host=self.qdrant_host, port=self.qdrant_port),
            collection_name=self.collection_name,
            embeddings=self.embedding_model
        )

        llm = GigaChat(
            credentials=self.giga_credentials,
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            temperature=0.3,
            verify_ssl_certs=False
        )

        prompt_template = """
Ты — цифровой юрист. Отвечай точно, ссылаясь на статьи Конституции РФ.
Если в контексте есть прямая цитата — используй её.
Если нет — скажи: "В предоставленном контексте нет точной информации".

Контекст:
{context}

Вопрос:
{question}

Ответ:
"""

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": PromptTemplate.from_template(prompt_template)},
            return_source_documents=True
        )

    def ask(self, question: str) -> dict:
        """Задает вопрос и возвращает ответ"""
        try:
            result = self.qa_chain.invoke({"query": question})
            return {
                "question": _clean_text(question),
                "answer": _clean_text(result["result"]),
                "sources": [
                    Document(
                        page_content=_clean_text(doc.page_content),
                        metadata={k: _clean_text(v) for k, v in doc.metadata.items()}
                    )
                    for doc in result["source_documents"]
                ]
            }
        except Exception as e:
            if "TextEncodeInput" in str(e):
                raise Exception("Ошибка обработки текста. Попробуйте переформулировать вопрос.")
            else:
                raise e