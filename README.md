# C4-архитектура — LocalScript AI Agent

## Уровень 1 — Контекст системы

```mermaid
graph TB
    User["Разработчик\nпользователь LowCode-платформы"]:::external

    subgraph "LocalScript AI Agent"
        System["LocalScript AI Agent\nГенерация Lua-кода из\nестественного языка"]:::system
    end

    User -->|"Отправляет задачу\n{prompt, context_json}"| System
    System -->|"Возвращает Lua-код\nили вопрос для уточнения"| User

    classDef system fill:#1168bd,color:#fff,stroke:#0b48a0
    classDef external fill:#999,color:#fff,stroke:#666
```

---

## Уровень 2 — Контейнеры

```mermaid
graph TB
    User["Пользователь"]:::external

    subgraph "Docker-сеть compose.yaml"
        subgraph "localscriptlua FastAPI Python 3.12"
            API["FastAPI Server\nпорт 8080\nsrc/main.py"]:::container
            Workflow["Механизм рабочих процессов LangGraph\nsrc/workflow/luacode_workflow.py"]:::container
            KB["База знаний\n120 файлов JSON\nknowledge_base/examples/"]:::container
            LuaRuntime["Среда выполнения Lua 5.4\nПроверка синтаксиса и выполнение в песочнице"]:::container
        end

        subgraph "Ollama ollama/ollama"
            Ollama["Ollama Server\nпорт 11434\nqwen2.5-coder:3b"]:::container
        end
    end

    User -->|"POST /generate"| API
    API -->|"Запуск рабочего процесса"| Workflow
    Workflow -->|"Поиск BM25"| KB
    Workflow -->|"Вывод LLM\nChatOllama"| Ollama
    Workflow -->|"Проверка и выполнение кода"| LuaRuntime

    classDef system fill:#1168bd,color:#fff,stroke:#0b48a0
    classDef external fill:#999,color:#fff,stroke:#666
    classDef container fill:#2d8539,color:#fff,stroke:#236b2d
```

---

## Уровень 3 — Компоненты механизма LangGraph

```mermaid
graph TB
    subgraph "Машина состояний LangGraph LuaCodeWorkflow"
        Parse["parse_input_node\nИзвлечение JSON\nочистка запроса"]:::component
        Clarify["clarify_request_node\nLLM запрос ясен\nили нужен вопрос t=0.2"]:::component
        Retrieve["retrieve_examples_node\nПоиск BM25\n3 лучших примера"]:::component
        Generate["generate_code_node\nLLM генерация Lua\nt=0.15 несколько примеров"]:::component
        Validate["validate_code_node\nПроверка loadfile\nпроверка паттернов"]:::component
        TestExec["test_execute_node\nВыполнение в песочнице\nс context_json"]:::component
        Refine["refine_code_node\nLLM исправление\nс учётом ошибок t=0.1"]:::component
        Increment["increment_retry_node\nСчётчик повторных попыток"]:::component
        RespondClar["respond_clarify_node\nВозврат вопроса\nпользователю"]:::component
        Fallback["fallback_clarify_node\nLLM вопрос при\nисчерпании попыток"]:::component
        Format["format_response_node\nУдаление разметки\nфинальный код"]:::component
    end

    subgraph "Состояние LuaWorkflowState"
        State["user_request context_json\nretrieved_examples generated_code\nvalidation_errors is_valid\nretry_count max_retries=2\nclarification_needed\nfinal_code test_success"]:::state
    end

    Parse --> Clarify
    Clarify -->|"требуется уточнение"| RespondClar
    Clarify -->|"запрос ясен"| Retrieve
    Retrieve --> Generate
    Generate --> Validate
    Validate -->|"код корректен"| TestExec
    Validate -->|"есть ошибки"| Refine
    TestExec -->|"выполнение успешно"| Format
    TestExec -->|"ошибка выполнения"| Refine
    Refine --> Increment
    Increment -->|"повторные попытки не исчерпаны"| Validate
    Increment -->|"повторные попытки исчерпаны"| Fallback
    Fallback --> Format
    RespondClar --> Format

    Parse -.-> State
    Clarify -.-> State
    Retrieve -.-> State
    Generate -.-> State
    Validate -.-> State
    TestExec -.-> State
    Refine -.-> State
    Format -.-> State

    classDef system fill:#1168bd,color:#fff,stroke:#0b48a0
    classDef external fill:#999,color:#fff,stroke:#666
    classDef container fill:#2d8539,color:#fff,stroke:#236b2d
    classDef component fill:#8e44ad,color:#fff,stroke:#6c3483
    classDef state fill:#f39c12,color:#000,stroke:#d68910,stroke-dasharray: 5 5
```

---

## Уровень 4 — Последовательность выполнения запроса

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant API as FastAPI порт 8080
    participant WF as Рабочий процесс LangGraph
    participant KB as База знаний
    participant Ollama as LLM Ollama
    participant Lua as Среда выполнения Lua

    U->>API: POST /generate {prompt, context}
    API->>WF: Запуск рабочего процесса

    WF->>WF: parse_input_node
    WF->>Ollama: clarify_request_node
    Ollama-->>WF: Требуется уточнение?

    alt Требуется уточнение
        WF-->>API: {clarification_question}
        API-->>U: Вопрос для уточнения
    else Запрос ясен
        WF->>KB: Поиск примеров BM25
        KB-->>WF: 3 лучших примера
        WF->>Ollama: generate_code_node
        Ollama-->>WF: Lua-код
        WF->>Lua: validate_code_node
        Lua-->>WF: Результат проверки

        loop Повторные попытки максимум 2
            alt Есть ошибки
                WF->>Lua: test_execute_node
                Lua-->>WF: Результат выполнения
                WF->>Ollama: refine_code_node
                Ollama-->>WF: Исправленный код
                WF->>Lua: Повторная проверка
                Lua-->>WF: Результат проверки
            else Код корректен
                WF->>WF: format_response_node
            end
        end

        WF-->>API: {final_code}
        API-->>U: Lua-код
    end
```
