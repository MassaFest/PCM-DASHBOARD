# PCM Dashboard

Dashboard de manutenção que consolida dados do Google Forms + retornos dos mecânicos.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy grátis no Streamlit Cloud

1. Criar conta em https://streamlit.io/cloud (login com GitHub)
2. Criar repositório no GitHub e subir esta pasta
3. Em "New app" → apontar para `app.py`
4. Clicar em "Deploy"

## Pré-requisito: deixar as planilhas públicas

As planilhas do Google precisam ter acesso **"Qualquer pessoa com o link pode visualizar"**:
- Abrir a planilha → Compartilhar → "Qualquer pessoa com o link" → Leitor

## Configuração das colunas

Na primeira vez que abrir o dashboard, use o menu lateral para mapear os nomes
das colunas conforme os cabeçalhos das suas planilhas.
