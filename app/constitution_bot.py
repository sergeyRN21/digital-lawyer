# constitution_bot.py

from dotenv import load_dotenv
from rag_engine import ConstitutionDocumentProcessor, ConstitutionRAG
import os
import re


def _clean_text(text: str) -> str:
    """Удаляет суррогаты и некорректные unicode-символы."""
    if not isinstance(text, str):
        return text
    # Удаляем символы из суррогатной области U+D800–U+DFFF
    return re.sub(r'[\ud800-\udfff]', '', text)


class ConstitutionBot:
    """Главный класс цифрового юриста"""

    def __init__(self):
        load_dotenv()
        self._validate_config()
        self.rag_engine = None
        self.initialized = False

    def _validate_config(self):
        """Проверяет конфигурацию"""
        self.giga_credentials = os.getenv("GIGACHAT_CREDENTIALS")
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))

        if not self.giga_credentials:
            raise ValueError("❗ Установите GIGACHAT_CREDENTIALS в файле .env")

    def initialize(self, data_path: str = "data/constitution_rf.txt"):
        """Инициализирует бота"""
        print("📚 Загружаем и обрабатываем Конституцию...")

        # Проверяем существование файла
        if not os.path.exists(data_path):
            # Пробуем альтернативный путь
            alt_path = f"app/{data_path}"
            if os.path.exists(alt_path):
                data_path = alt_path
            else:
                raise FileNotFoundError(f"Файл конституции не найден: {data_path} или {alt_path}")

        print(f"📖 Используем файл: {data_path}")

        # Обработка документов
        processor = ConstitutionDocumentProcessor(data_path)
        documents = processor.create_documents()
        print(f"✅ Создано {len(documents)} документов")

        # Инициализация RAG
        self.rag_engine = ConstitutionRAG(
            giga_credentials=self.giga_credentials,
            qdrant_host=self.qdrant_host,
            qdrant_port=self.qdrant_port
        )

        print("🧠 Инициализируем RAG движок...")
        self.rag_engine.initialize(documents)
        self.initialized = True
        print("✅ Цифровой юрист готов к работе!")

    def ask_question(self, question: str) -> str:
        """Задает вопрос и возвращает ответ"""
        if not self.initialized:
            raise Exception("Бот не инициализирован. Вызовите initialize() сначала.")

        result = self.rag_engine.ask(question)
        return self._format_response(result)

    def _format_response(self, result: dict) -> str:
        """Форматирует ответ для вывода, очищая текст"""
        answer = _clean_text(result['answer'])
        response = f"\n💬 {answer}"

        if result['sources']:
            response += "\n\n📄 Источники:"
            for i, doc in enumerate(result['sources'][:2], 1):
                article = _clean_text(doc.metadata.get("article", "Неизвестно"))
                part_info = f" (часть {doc.metadata.get('part')})" if doc.metadata.get('part') else ""
                snippet = _clean_text(doc.page_content[:200])
                response += f"\n  [{i}] {article}{part_info}: {snippet}..."

        return response

    def run_interactive(self):
        """Запускает интерактивный режим"""
        if not self.initialized:
            raise Exception("Бот не инициализирован.")

        print("\n" + "=" * 50)
        print("🤖 Цифровой юрист готов!")
        print("Задайте вопрос или 'выход'")
        print("=" * 50)

        while True:
            question = input("\nВаш вопрос: ").strip()
            if question.lower() in ["выход", "exit", "quit"]:
                break
            if not question:
                continue

            try:
                print("🔍 Обрабатываю запрос...")
                response = self.ask_question(question)
                print(response)
            except Exception as e:
                print(f"❌ {e}")


if __name__ == "__main__":
    bot = ConstitutionBot()
    bot.initialize()
    bot.run_interactive()