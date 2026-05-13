# MyFi Architecture

## Core vs Chunks vs Plugins

| Conceito | O que é | Onde vive | Exemplo |
|----------|---------|-----------|---------|
| **Core** | Lógica de negócio essencial (sempre ativa) | `myfi/core/` | `MonitorCore.py`, `scanner.py`, `alerts.py` |
| **Chunk** | Módulo de lógica de negócio reutilizável, encadeável em workflows | `myfi/chunks/extras/` | `TelegramNotifierChunk`, `GoogleIntelChunk` |
| **Plugin** | Capacidade técnica pura usada pelos Chunks | `myfi/plugins/` | `AlertManager`, `GoogleIntelPlugin` |

## Regra Ninja

Se um módulo toma decisões **sobre o que fazer**, é um **Chunk**.  
Se um módulo sabe **como fazer** algo tecnicamente, é um **Plugin**.

## Fluxo de Execução

1. `ChunkEngine` carrega os Chunks registados.
2. Um Workflow é disparado (via CLI `myfi workflow run`, ou via agendamento, ou via trigger do monitor).
3. Cada Chunk no Workflow recebe `input_data`, executa a sua lógica, e devolve `output_data` para o próximo Chunk.
4. Durante a execução, um Chunk pode chamar um ou mais Plugins para realizar tarefas técnicas (enviar uma mensagem, consultar uma API, correr um comando).

## Estrutura de Pastas

src/myfi/
├── core/                  # Lógica de negócio essencial
├── chunks/
│   ├── core/              # Chunks sempre ativos
│   └── extras/            # Chunks opcionais
├── plugins/               # Capacidades técnicas
├── ui/                    # Interface (CLI + Web)
├── db/                    # Base de dados
└── blacklabel/            # Módulos de estudo avançado (privados)
