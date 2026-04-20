# Contribuindo para o MyFi

Obrigado por considerar contribuir! Este documento ajuda a manter o projeto organizado.

## Como posso contribuir?

### Reportar problemas (Issues)
- Use o template de **Bug Report**.
- Inclua: passo a passo para reproduzir, sistema operativo, versão do Python, e o que esperava que acontecesse.

### Sugerir melhorias
- Abra uma **Issue** com o prefixo `[IDEA]`.
- Explique o problema que a sua ideia resolve e como imagina a implementação.

### Pull Requests
1. **Comunique primeiro** – abra uma Issue para discutir a mudança.
2. **Siga o estilo de código** – PEP8, nomes descritivos, comentários quando necessário.
3. **Commits semânticos**:
   - `feat:` nova funcionalidade
   - `fix:` correção de bug
   - `docs:` documentação
   - `refactor:` reestruturação (sem alterar comportamento)
   - `test:` testes
   - `chore:` manutenção (deps, configs)
4. **Teste as suas alterações** – garanta que `python main.py scan` continua a funcionar.
5. **Envie o PR para a branch `dev`** (não para `main`).

## Ambiente de desenvolvimento

```bash
git clone https://github.com/lioexp/myfi.git
cd myfi
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
python main.py setup        # primeira execução
python main.py scan         # testar scanner
