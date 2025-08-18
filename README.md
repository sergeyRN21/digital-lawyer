# 🤖 Цифровой Юрист (Constitution Bot)

ИИ-ассистент для ответов на вопросы по Конституции Российской Федерации с использованием RAG (Retrieval-Augmented Generation) технологии.

## 📋 Описание

Проект представляет собой интерактивного цифрового юриста, который:
- Загружает и обрабатывает текст Конституции РФ
- Разбивает документ на статьи и чанки
- Создаёт векторную базу знаний с помощью Qdrant
- Использует модель эмбеддингов `intfloat/multilingual-e5-large`
- Применяет LLM GigaChat для генерации ответов
- Предоставляет ссылки на источники в Конституции

## 🏗️ Архитектура

```mermaid
graph TD
    A[Пользователь] --> B[ConstitutionBot]
    B --> C[RAG Engine]
    C --> D[Document Processor]
    D --> E[constitution_rf.txt]
    C --> F[Qdrant Manager]
    F --> G[Qdrant DB]
    C --> H[GigaChat LLM]
    C --> I[Embeddings Model]