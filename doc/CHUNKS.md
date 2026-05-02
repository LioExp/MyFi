# Como Criar um Novo Chunk

## 1. Criar o Plugin (se necessário)

Se o teu Chunk precisa de uma capacidade técnica que ainda não existe (ex: consultar a API do Google), cria um ficheiro em `myfi/plugins/`.

Exemplo: `myfi/plugins/google_intel_plugin.py`

## 2. Criar o Chunk

Cria um ficheiro em `myfi/chunks/extras/`. O Chunk deve herdar de `BaseChunk` e implementar:

- `manifest()`: metadados (nome, versão, entradas, saídas, permissões)
- `run(input_data)`: a lógica do Chunk

## 3. Registar o Chunk

O Chunk pode ser registado manualmente no `ChunkEngine` ou automaticamente se estiver na pasta `chunks/extras/` e o motor o carregar.

## 4. Testar

```bash
myfi chunk list                 # ver se aparece
myfi workflow run meu_workflow  # executar
